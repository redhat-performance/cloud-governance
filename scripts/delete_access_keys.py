#!/usr/bin/env python3
"""
Scan every IAM access key in one AWS account and report the keys that were created
more than a threshold number of days ago (default: 3).

This script is standalone: it depends only on boto3 and imports nothing from
cloud_governance, so it can be copied out of this repository and run anywhere.

Credentials and region are resolved the usual boto3 way (environment variables,
AWS profile, instance role), or explicitly with --profile / --region.

The default mode only reports. Keys can be changed in two deliberate phases:

    --deactivate   Active -> Inactive. Reversible; stops the key from working.
    --delete       Delete keys. Only Inactive keys are eligible by default.

Both phases are dry runs unless --apply is given, so the same command can be
previewed first and executed second. Deleting an access key is irreversible.

Safety rules that apply to every mutation:
  * the caller's own access key is never touched;
  * a user's last Active key is never touched unless --force is given;
  * keys listed in EXCLUDE_ACCESS_KEY_IDS or --exclude-key-id are never touched;
  * a failure on one key does not stop the run; it is reported and the scan
    continues (the exit status is 1 when any key failed).

By default the report never prints access key ids or secrets: a key is identified by
its IAM user and its position ("Access key 1" is the oldest of that user's keys).
Pass --show-key-ids to include the id of each matching key.

Exit status: 1 when at least one key is older than the threshold or a user's keys
could not be read (report mode), or when any action failed (action mode), 0
otherwise. Use --exit-zero to always return 0.

Examples:
    python scripts/delete_access_keys.py
    python scripts/delete_access_keys.py --days 30 --profile prod --json
    python scripts/delete_access_keys.py --output-file /tmp/old-keys.txt
    python scripts/delete_access_keys.py --deactivate            # preview
    python scripts/delete_access_keys.py --deactivate --apply    # execute
    python scripts/delete_access_keys.py --delete --apply        # later, Inactive only
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

DEFAULT_THRESHOLD_DAYS = 3
DEFAULT_REGION = 'us-east-1'
ACTIONS = ('deactivate', 'delete')
PAST_TENSE = {'deactivate': 'deactivated', 'delete': 'deleted'}
ACTION_LABEL = {'deactivate': 'DEACTIVATE', 'delete': 'DELETE'}
EXCLUDE_ENV_VAR = 'EXCLUDE_ACCESS_KEY_IDS'


def parse_args(argv=None):
    """
    Parses the command line arguments.
    :param argv: Argument list (defaults to sys.argv[1:]).
    :return: Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description='Report, deactivate or delete IAM access keys created more than '
                    'N days ago.')
    parser.add_argument(
        '--days', type=int, default=DEFAULT_THRESHOLD_DAYS,
        help=f'Select keys older than this many days (default: {DEFAULT_THRESHOLD_DAYS}).')
    parser.add_argument(
        '--profile', default=None,
        help='AWS profile to use. Defaults to the standard boto3 credential chain.')
    parser.add_argument(
        '--region', default=os.environ.get('AWS_DEFAULT_REGION') or DEFAULT_REGION,
        help='Region used to create the IAM client; IAM itself is global '
             f'(default: {DEFAULT_REGION}).')
    parser.add_argument(
        '--json', action='store_true',
        help='Print the report as JSON instead of text.')
    parser.add_argument(
        '--show-key-ids', action='store_true',
        help='Include access key ids in the output. Off by default so ids are not '
             'written to logs or terminal scrollback.')
    parser.add_argument(
        '--sort', choices=('user', 'age'), default='user',
        help='Sort order of the report: user (alphabetical, default) or age '
             '(oldest key first).')
    parser.add_argument(
        '--output-file', default=None, metavar='PATH',
        help='Write the complete report to PATH instead of stdout. Use this when '
             'the terminal truncates long output.')
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        '--deactivate', dest='action', action='store_const', const='deactivate',
        help='Deactivate selected Active keys. Reversible. Dry run without --apply.')
    action_group.add_argument(
        '--delete', dest='action', action='store_const', const='delete',
        help='Delete selected keys. Irreversible. Only Inactive keys are eligible '
             'unless --include-active is given. Dry run without --apply.')
    parser.add_argument(
        '--apply', action='store_true',
        help='Actually perform the selected action. Without it the action is only '
             'previewed.')
    parser.add_argument(
        '--include-active', action='store_true',
        help='With --delete, also allow deleting Active keys. The last Active key '
             'of a user still requires --force.')
    parser.add_argument(
        '--force', action='store_true',
        help="Allow acting on a user's last Active key. This removes all "
             'programmatic access for that user. The caller key is never touched.')
    parser.add_argument(
        '--exclude-key-id', action='append', default=None, metavar='KEY_ID',
        help=f'Never act on this access key id. Repeatable. Prefer the '
             f'{EXCLUDE_ENV_VAR} environment variable (comma separated) so the id '
             f'does not end up in shell history.')
    parser.add_argument(
        '--exit-zero', action='store_true',
        help='Always exit 0, even when keys are found or an action fails.')
    return parser.parse_args(argv)


def validate_args(args) -> int:
    """
    Rejects combinations that would be ambiguous or unsafe.
    :param args: Parsed arguments.
    :return: 0 when valid, 2 otherwise.
    """
    if args.days < 0:
        print('error: --days must be zero or greater', file=sys.stderr)
        return 2
    if args.apply and not args.action:
        print('error: --apply requires --deactivate or --delete', file=sys.stderr)
        return 2
    if args.include_active and args.action != 'delete':
        print('error: --include-active requires --delete', file=sys.stderr)
        return 2
    if args.force and not args.action:
        print('error: --force requires --deactivate or --delete', file=sys.stderr)
        return 2
    return 0


def excluded_key_ids(args) -> set:
    """
    Collects the access key ids that must never be touched, from the command line
    and from the EXCLUDE_ACCESS_KEY_IDS environment variable.
    :param args: Parsed arguments.
    :return: Set of access key ids.
    """
    ids = set(args.exclude_key_id or [])
    env_value = os.environ.get(EXCLUDE_ENV_VAR, '')
    ids.update(part.strip() for part in env_value.split(',') if part.strip())
    return ids


def caller_access_key(session) -> str:
    """
    Returns the access key id the script itself is using, so it is never modified.
    Works for environment credentials and shared-credentials-file alike.
    :param session: The boto3 session used for the run.
    :return: The caller's access key id, or None when the caller uses a role.
    """
    credentials = session.get_credentials()
    return credentials.access_key if credentials else None


def get_old_access_keys(iam_client, threshold_days: int):
    """
    Lists every IAM user and collects the access keys whose CreateDate is older than
    threshold_days. Users are paginated; a user that cannot be read is reported in
    the errors list instead of aborting the whole scan.

    :param iam_client: A boto3 IAM client.
    :param threshold_days: Minimum age in days for a key to be reported.
    :return: (findings, errors, users_scanned) where findings is a list of dicts
        sorted alphabetically by user name, errors is a list of
        (username, error_code) tuples and users_scanned is the number of IAM users
        visited.
    """
    now = datetime.now(timezone.utc)
    findings = []
    errors = []
    users_scanned = 0

    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']
            users_scanned += 1
            try:
                metadata = iam_client.list_access_keys(
                    UserName=username)['AccessKeyMetadata']
            except ClientError as err:
                # The message contains the caller ARN; keep only the error code.
                code = err.response.get('Error', {}).get('Code', 'unknown')
                errors.append((username, code))
                continue

            # Sort oldest first so the label matches the rest of the code base
            # ("Access key 1" is the oldest key, "Access key 2" the newer one).
            metadata.sort(key=lambda key: key['CreateDate'])
            active_keys = sum(1 for key in metadata if key['Status'] == 'Active')
            for index, key in enumerate(metadata, start=1):
                create_date = key['CreateDate']
                age = now - create_date
                # Compare the full age, not the truncated day count: a key aged
                # "3 days 23 hours" is older than 3 days and must be reported.
                if age > timedelta(days=threshold_days):
                    findings.append({
                        'username': username,
                        'label': f'Access key {index}',
                        'status': key['Status'],
                        'created': create_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'age_days': age.days,
                        'access_key_id': key['AccessKeyId'],
                        'active_keys': active_keys,
                    })

    findings.sort(key=lambda finding: (finding['username'].lower(),
                                       finding['label']))
    return findings, errors, users_scanned


def skip_reason(finding, action: str, include_active: bool, force: bool,
                caller_key_id, excluded_ids: set, remaining_active: dict):
    """
    Decides whether a finding must be left alone, and why.
    :param finding: One entry from get_old_access_keys.
    :param action: 'deactivate' or 'delete'.
    :param include_active: Whether Active keys may be deleted.
    :param force: Whether a user's last Active key may be acted on.
    :param caller_key_id: The key the script is running with, or None.
    :param excluded_ids: Access key ids that must never be touched.
    :param remaining_active: Active key count per user, decremented as keys are acted on.
    :return: A human-readable reason, or None when the key may be acted on.
    """
    if caller_key_id and finding['access_key_id'] == caller_key_id:
        return "caller's own key"
    if finding['access_key_id'] in excluded_ids:
        return 'excluded by --exclude-key-id'
    if action == 'deactivate' and finding['status'] != 'Active':
        return 'already inactive'
    if action == 'delete' and finding['status'] != 'Inactive' and not include_active:
        return 'active key requires --include-active'
    if (finding['status'] == 'Active' and not force
            and remaining_active[finding['username']] <= 1):
        return "user's last active key (use --force)"
    return None


def apply_action(iam_client, action: str, finding):
    """
    Performs one mutation.
    :param iam_client: A boto3 IAM client.
    :param action: 'deactivate' or 'delete'.
    :param finding: The key to change.
    :return: None on success, otherwise the AWS error code.
    """
    try:
        if action == 'deactivate':
            iam_client.update_access_key(
                UserName=finding['username'],
                AccessKeyId=finding['access_key_id'],
                Status='Inactive')
        else:
            iam_client.delete_access_key(
                UserName=finding['username'],
                AccessKeyId=finding['access_key_id'])
    except ClientError as err:
        return err.response.get('Error', {}).get('Code', 'unknown')
    return None


def execute_actions(iam_client, findings, action: str, apply: bool,
                    include_active: bool, force: bool, caller_key_id,
                    excluded_ids: set) -> dict:
    """
    Walks the findings, decides what may be changed, and mutates when apply is True.
    A user's last Active key is never changed without force; the remaining Active
    count is tracked per user so two keys are not both acted on in one run.
    :return: dict with 'acted', 'skipped' and 'failed' lists.
    """
    remaining_active = {}
    acted, skipped, failed = [], [], []
    for finding in findings:
        username = finding['username']
        remaining_active.setdefault(username, finding['active_keys'])
        reason = skip_reason(finding, action, include_active, force,
                             caller_key_id, excluded_ids, remaining_active)
        if reason:
            skipped.append({**finding, 'reason': reason})
            continue

        entry = dict(finding)
        if apply:
            error_code = apply_action(iam_client, action, finding)
            if error_code == 'NoSuchEntity' and action == 'delete':
                skipped.append({**finding, 'reason': 'already absent'})
                continue
            if error_code:
                failed.append({**entry, 'error': error_code})
                continue
        if finding['status'] == 'Active':
            remaining_active[username] -= 1
        acted.append(entry)
    return {'acted': acted, 'skipped': skipped, 'failed': failed}


def build_rows(findings, show_key_ids: bool):
    """
    Converts the findings into table rows, dropping the key id unless asked for.
    :param findings: Return value of get_old_access_keys.
    :param show_key_ids: Whether to include the access key id column.
    :return: (header, rows) as lists of strings.
    """
    header = ['USER', 'KEY', 'STATUS', 'CREATED (UTC)', 'AGE (DAYS)']
    if show_key_ids:
        header.insert(1, 'ACCESS KEY ID')
    rows = []
    for finding in findings:
        row = [
            finding['username'],
            finding['label'],
            finding['status'],
            finding['created'],
            str(finding['age_days']),
        ]
        if show_key_ids:
            row.insert(1, finding['access_key_id'])
        rows.append(row)
    return header, rows


def format_table(header, rows):
    """
    Formats a left-aligned text table.
    :param header: Column titles.
    :param rows: Table rows, each with the same width as the header.
    :return: The table as a list of lines.
    """
    widths = [max(len(str(cell)) for cell in column)
              for column in zip(header, *rows)]
    lines = ['  '.join(title.ljust(width)
                       for title, width in zip(header, widths)),
             '  '.join('-' * width for width in widths)]
    lines.extend('  '.join(str(cell).ljust(width)
                           for cell, width in zip(row, widths))
                 for row in rows)
    return lines


def render_report(findings, errors, threshold_days: int, show_key_ids: bool,
                  users_scanned: int) -> str:
    """
    Renders the human-readable report. It is returned as a string rather than
    printed so the full report can also be written to a file, which is not
    subject to terminal scrollback limits.
    :param findings: Findings returned by get_old_access_keys.
    :param errors: Errors returned by get_old_access_keys.
    :param threshold_days: Threshold used for the summary line.
    :param show_key_ids: Whether the key id column is included.
    :param users_scanned: Number of IAM users visited by the scan.
    :return: The complete report.
    """
    lines = [f'Scanned {users_scanned} IAM user(s); {len(findings)} access key(s) '
             f'older than {threshold_days} day(s).']
    if findings:
        lines.append('')
        header, rows = build_rows(findings, show_key_ids)
        lines.extend(format_table(header, rows))
    for username, code in errors:
        lines.append(f'WARNING: could not list access keys for user '
                     f'{username!r} ({code})')
    return '\n'.join(lines)


def summarize_actions(result: dict, action: str, apply: bool) -> list:
    """
    Builds the action lines and the summary line(s) of an action report.
    :param result: Return value of execute_actions.
    :param action: 'deactivate' or 'delete'.
    :param apply: Whether the action was executed.
    :return: Report lines.
    """
    lines = []
    verb = ACTION_LABEL[action] if apply else f'WOULD {ACTION_LABEL[action]}'
    for entry in result['acted']:
        lines.append(f'{verb}  {entry["username"]}  {entry["label"]}  '
                     f'{entry["status"]}  {entry["age_days"]}d')
    for entry in result['failed']:
        lines.append(f'FAILED  {entry["username"]}  {entry["label"]}  '
                     f'({entry["error"]})')

    acted = len(result['acted'])
    lead = PAST_TENSE[action].capitalize() if apply else f'Would {action}'
    summary = (f'{lead} {acted}, skipped {len(result["skipped"])}, '
               f'failed {len(result["failed"])}.')
    lines.append(summary)

    reasons = {}
    for entry in result['skipped']:
        reasons[entry['reason']] = reasons.get(entry['reason'], 0) + 1
    if reasons:
        breakdown = ', '.join(f'{reason} ({count})' for reason, count
                              in sorted(reasons.items(), key=lambda item: -item[1]))
        lines.append(f'Skipped: {breakdown}')
    return lines


def render_action_report(result: dict, errors, action: str, apply: bool,
                         threshold_days: int, users_scanned: int,
                         findings_count: int) -> str:
    """
    Renders the human-readable report for an action run.
    :param result: Return value of execute_actions.
    :param errors: Errors returned by get_old_access_keys.
    :param action: 'deactivate' or 'delete'.
    :param apply: Whether the action was executed.
    :param threshold_days: Threshold used for the summary line.
    :param users_scanned: Number of IAM users visited by the scan.
    :param findings_count: Number of candidate keys.
    :return: The complete report.
    """
    mode = 'applied' if apply else 'dry run; pass --apply to execute'
    lines = [
        f'Scanned {users_scanned} IAM user(s); {findings_count} access key(s) '
        f'older than {threshold_days} day(s).',
        f'Mode: {action} ({mode})',
        '',
    ]
    lines.extend(summarize_actions(result, action, apply))
    for username, code in errors:
        lines.append(f'WARNING: could not list access keys for user '
                     f'{username!r} ({code})')
    return '\n'.join(lines)


def report_scan_error(error_code=None) -> int:
    """
    Prints the reason the scan could not run.
    :param error_code: AWS error code, or None when no credentials were found.
    :return: The process exit status to use (2).
    """
    if error_code is None:
        print('error: no AWS credentials found', file=sys.stderr)
        return 2
    print(f'error: unable to scan IAM access keys ({error_code})', file=sys.stderr)
    if error_code == 'InvalidClientTokenId':
        print('hint: this usually means the access key is invalid, deleted or '
              'deactivated; refresh the credentials and try again.',
              file=sys.stderr)
    return 2


def strip_key_ids(entries, show_key_ids: bool) -> list:
    """
    Removes access key ids from report entries unless they were requested.
    :param entries: Report entries.
    :param show_key_ids: Whether access key ids are included.
    :return: Sanitized entries.
    """
    return [
        {key: value for key, value in entry.items()
         if key != 'access_key_id' or show_key_ids}
        for entry in entries
    ]


def build_json_payload(findings, errors, threshold_days: int, show_key_ids: bool,
                       users_scanned: int) -> str:
    """
    Builds the JSON report for a scan-only run.
    :param findings: Findings returned by get_old_access_keys.
    :param errors: Errors returned by get_old_access_keys.
    :param threshold_days: Threshold used for the scan.
    :param show_key_ids: Whether access key ids are included.
    :param users_scanned: Number of IAM users visited by the scan.
    :return: The JSON report.
    """
    payload = {
        'threshold_days': threshold_days,
        'users_scanned': users_scanned,
        'count': len(findings),
        'keys': strip_key_ids(findings, show_key_ids),
        'errors': [
            {'username': username, 'error': code}
            for username, code in errors
        ],
    }
    return json.dumps(payload, indent=2)


def build_action_json_payload(result: dict, errors, action: str, apply: bool,
                              threshold_days: int, show_key_ids: bool,
                              users_scanned: int, findings_count: int) -> str:
    """
    Builds the JSON report for an action run.
    :param result: Return value of execute_actions.
    :param errors: Errors returned by get_old_access_keys.
    :param action: 'deactivate' or 'delete'.
    :param apply: Whether the action was executed.
    :param threshold_days: Threshold used for the scan.
    :param show_key_ids: Whether access key ids are included.
    :param users_scanned: Number of IAM users visited by the scan.
    :param findings_count: Number of candidate keys.
    :return: The JSON report.
    """
    payload = {
        'threshold_days': threshold_days,
        'users_scanned': users_scanned,
        'candidates': findings_count,
        'action': action,
        'applied': apply,
        'acted': strip_key_ids(result['acted'], show_key_ids),
        'skipped': strip_key_ids(result['skipped'], show_key_ids),
        'failed': strip_key_ids(result['failed'], show_key_ids),
        'errors': [
            {'username': username, 'error': code}
            for username, code in errors
        ],
    }
    return json.dumps(payload, indent=2)


def write_report(content: str, output_file, findings_count: int,
                 users_scanned: int) -> int:
    """
    Writes the report to a file, or to stdout when no file is configured.
    :param content: Report body.
    :param output_file: Destination path, or None for stdout.
    :param findings_count: Number of findings, used in the confirmation line.
    :param users_scanned: Number of IAM users visited by the scan.
    :return: 0 on success, 2 when the file cannot be written.
    """
    if not output_file:
        print(content)
        return 0
    try:
        with open(output_file, 'w', encoding='utf-8') as report_file:
            report_file.write(content + '\n')
    except OSError as err:
        print(f'error: cannot write {output_file!r}: {err}', file=sys.stderr)
        return 2
    print(f'Wrote {findings_count} finding(s) from {users_scanned} scanned '
          f'user(s) to {output_file}')
    return 0


def run_action_mode(args, iam_client, session, findings, errors, users_scanned) -> int:
    """
    Runs the deactivate/delete phase and writes its report.
    :param args: Parsed arguments.
    :param iam_client: A boto3 IAM client.
    :param session: The boto3 session, used to identify the caller key.
    :param findings: Findings returned by get_old_access_keys.
    :param errors: Errors returned by get_old_access_keys.
    :param users_scanned: Number of IAM users visited by the scan.
    :return: Process exit status.
    """
    result = execute_actions(
        iam_client, findings, args.action, args.apply, args.include_active,
        args.force, caller_access_key(session), excluded_key_ids(args))

    if args.json:
        content = build_action_json_payload(
            result, errors, args.action, args.apply, args.days,
            args.show_key_ids, users_scanned, len(findings))
    else:
        content = render_action_report(
            result, errors, args.action, args.apply, args.days,
            users_scanned, len(findings))

    status = write_report(content, args.output_file, len(findings), users_scanned)
    if status:
        return status
    if result['failed'] and not args.exit_zero:
        return 1
    return 0


def run_report_mode(args, findings, errors, users_scanned) -> int:
    """
    Runs the report-only phase and writes its report.
    :param args: Parsed arguments.
    :param findings: Findings returned by get_old_access_keys.
    :param errors: Errors returned by get_old_access_keys.
    :param users_scanned: Number of IAM users visited by the scan.
    :return: Process exit status.
    """
    if args.json:
        content = build_json_payload(findings, errors, args.days,
                                     args.show_key_ids, users_scanned)
    else:
        content = render_report(findings, errors, args.days,
                                args.show_key_ids, users_scanned)

    status = write_report(content, args.output_file, len(findings), users_scanned)
    if status:
        return status
    # An unreadable user means the report is incomplete: never report success for
    # a scan that could not answer for every user.
    if (findings or errors) and not args.exit_zero:
        return 1
    return 0


def main(argv=None) -> int:
    """
    Entry point.
    :param argv: Argument list (defaults to sys.argv[1:]).
    :return: Process exit status.
    """
    args = parse_args(argv)
    invalid = validate_args(args)
    if invalid:
        return invalid

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    iam_client = session.client('iam')

    try:
        findings, errors, users_scanned = get_old_access_keys(iam_client, args.days)
    except NoCredentialsError:
        return report_scan_error()
    except ClientError as err:
        return report_scan_error(err.response.get('Error', {}).get('Code', 'unknown'))

    if args.sort == 'age':
        findings.sort(key=lambda finding: finding['age_days'], reverse=True)

    if args.action:
        return run_action_mode(args, iam_client, session, findings, errors,
                               users_scanned)
    return run_report_mode(args, findings, errors, users_scanned)


if __name__ == '__main__':
    sys.exit(main())
