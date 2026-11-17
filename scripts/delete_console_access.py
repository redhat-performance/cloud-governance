#!/usr/bin/env python3
"""
Report and remove console access for IAM users in one AWS account.

Console access for an IAM user means a login profile: a console password.
Removing it (DeleteLoginProfile) means the user can no longer sign in to the AWS
Management Console with a password. Access keys and MFA devices are not touched.

This script is standalone: it depends only on boto3 and imports nothing from
cloud_governance.

What this does NOT affect:
  * the root account always has console access;
  * IAM Identity Center (SSO) users are not IAM users and are not listed;
  * console access through assumed roles or federation is unrelated to login
    profiles;
  * access keys keep working, because they are programmatic credentials.

The default mode only reports. Removing requires --remove, and the removal is a
dry run unless --apply is also given. The caller's own IAM user is skipped unless
--include-caller is given, so the run cannot lock the operator out.

Exit status: 1 when at least one user has console access or a login profile could
not be read (report mode), or when any removal failed (action mode), 0 otherwise.
Use --exit-zero to always return 0.

Examples:
    python scripts/delete_console_access.py
    python scripts/delete_console_access.py --json --output-file /tmp/console.txt
    python scripts/delete_console_access.py --remove              # preview
    python scripts/delete_console_access.py --remove --apply      # execute
"""
import argparse
import json
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

DEFAULT_REGION = 'us-east-1'
EXCLUDE_ENV_VAR = 'EXCLUDE_IAM_USERS'


def parse_args(argv=None):
    """
    Parses the command line arguments.
    :param argv: Argument list (defaults to sys.argv[1:]).
    :return: Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Report or remove IAM users' console access (login profile).")
    parser.add_argument(
        '--profile', default=None,
        help='AWS profile to use. Defaults to the standard boto3 credential chain.')
    parser.add_argument(
        '--region', default=os.environ.get('AWS_DEFAULT_REGION') or DEFAULT_REGION,
        help='Region used to create the clients; IAM is global '
             f'(default: {DEFAULT_REGION}).')
    parser.add_argument(
        '--json', action='store_true',
        help='Print the report as JSON instead of text.')
    parser.add_argument(
        '--output-file', default=None, metavar='PATH',
        help='Write the complete report to PATH instead of stdout.')
    parser.add_argument(
        '--remove', action='store_true',
        help='Remove console access for the selected users. Dry run without '
             '--apply.')
    parser.add_argument(
        '--apply', action='store_true',
        help='Actually remove console access. Without it the removal is only '
             'previewed.')
    parser.add_argument(
        '--include-caller', action='store_true',
        help="Also remove the caller's own console access. Skipped by default so "
             'the operator is not locked out.')
    parser.add_argument(
        '--exclude-user', action='append', default=None, metavar='NAME',
        help=f'Never remove console access for this IAM user. Repeatable. Prefer '
             f'the {EXCLUDE_ENV_VAR} environment variable (comma separated).')
    parser.add_argument(
        '--exit-zero', action='store_true',
        help='Always exit 0.')
    return parser.parse_args(argv)


def validate_args(args) -> int:
    """
    Rejects combinations that would be ambiguous or unsafe.
    :param args: Parsed arguments.
    :return: 0 when valid, 2 otherwise.
    """
    if args.apply and not args.remove:
        print('error: --apply requires --remove', file=sys.stderr)
        return 2
    if args.include_caller and not args.remove:
        print('error: --include-caller requires --remove', file=sys.stderr)
        return 2
    return 0


def excluded_users(args) -> set:
    """
    Collects the user names that must never be changed, from the command line and
    from the EXCLUDE_IAM_USERS environment variable.
    :param args: Parsed arguments.
    :return: Set of IAM user names.
    """
    names = set(args.exclude_user or [])
    env_value = os.environ.get(EXCLUDE_ENV_VAR, '')
    names.update(part.strip() for part in env_value.split(',') if part.strip())
    return names


def caller_user_name(session):
    """
    Returns the IAM user name behind the credentials the script is running with,
    so that user's console access is skipped by default.
    :param session: The boto3 session used for the run.
    :return: The caller's IAM user name, or None when the caller is a role or root.
    """
    try:
        arn = session.client('sts').get_caller_identity()['Arn']
    except (ClientError, BotoCoreError):
        return None
    marker = ':user/'
    if marker not in arn:
        return None
    # arn:aws:iam::<account>:user/<path>/<name>; the user name is the last segment.
    return arn.split(marker, 1)[1].rsplit('/', 1)[-1]


def format_date(value) -> str:
    """
    Formats an optional datetime returned by IAM.
    :param value: A datetime or None.
    :return: UTC timestamp, or 'never'.
    """
    return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else 'never'


def get_console_users(iam_client):
    """
    Lists every IAM user and collects those that have a login profile, which is
    what grants console access.

    :param iam_client: A boto3 IAM client.
    :return: (findings, errors, users_scanned) where findings is a list of dicts
        sorted alphabetically, errors is a list of (username, error_code) tuples
        and users_scanned is the number of IAM users visited.
    """
    findings = []
    errors = []
    users_scanned = 0

    for page in iam_client.get_paginator('list_users').paginate():
        for user in page['Users']:
            username = user['UserName']
            users_scanned += 1
            try:
                profile = iam_client.get_login_profile(
                    UserName=username)['LoginProfile']
            except ClientError as err:
                # Keep only the code: the message can contain the caller ARN.
                code = err.response.get('Error', {}).get('Code', 'unknown')
                if code == 'NoSuchEntity':
                    # No login profile: the user has no console access.
                    continue
                errors.append((username, code))
                continue

            findings.append({
                'username': username,
                'password_created': format_date(profile.get('CreateDate')),
                'reset_required': bool(profile.get('PasswordResetRequired')),
                'last_console_sign_in': format_date(user.get('PasswordLastUsed')),
            })

    findings.sort(key=lambda finding: finding['username'].lower())
    return findings, errors, users_scanned


def skip_reason(finding, caller_user, excluded: set):
    """
    Decides whether a user must be left alone, and why.
    :param finding: One entry from get_console_users.
    :param caller_user: The caller's own IAM user name, or None.
    :param excluded: User names that must never be changed.
    :return: A human-readable reason, or None when console access may be removed.
    """
    if caller_user and finding['username'] == caller_user:
        return "caller's own user (use --include-caller)"
    if finding['username'] in excluded:
        return 'excluded by --exclude-user'
    return None


def remove_login_profile(iam_client, username: str):
    """
    Deletes the user's login profile, removing console access.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    :return: None on success, otherwise the AWS error code.
    """
    try:
        iam_client.delete_login_profile(UserName=username)
    except ClientError as err:
        return err.response.get('Error', {}).get('Code', 'unknown')
    return None


def execute_removals(iam_client, findings, apply: bool, caller_user,
                     excluded: set) -> dict:
    """
    Walks the findings and removes console access when apply is True.
    :param iam_client: A boto3 IAM client.
    :param findings: Findings returned by get_console_users.
    :param apply: Whether to actually remove console access.
    :param caller_user: The caller's own IAM user name, or None.
    :param excluded: User names that must never be changed.
    :return: dict with 'removed', 'skipped' and 'failed' lists.
    """
    removed, skipped, failed = [], [], []
    for finding in findings:
        reason = skip_reason(finding, caller_user, excluded)
        if reason:
            skipped.append({**finding, 'reason': reason})
            continue
        if apply:
            error_code = remove_login_profile(iam_client, finding['username'])
            if error_code == 'NoSuchEntity':
                skipped.append({**finding, 'reason': 'already absent'})
                continue
            if error_code:
                failed.append({**finding, 'error': error_code})
                continue
        removed.append(dict(finding))
    return {'removed': removed, 'skipped': skipped, 'failed': failed}


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


def build_rows(findings):
    """
    Converts the findings into table rows.
    :param findings: Findings returned by get_console_users.
    :return: (header, rows) as lists of strings.
    """
    header = ['USER', 'PASSWORD CREATED (UTC)', 'RESET REQUIRED',
              'LAST CONSOLE SIGN-IN']
    rows = [[finding['username'], finding['password_created'],
             str(finding['reset_required']), finding['last_console_sign_in']]
            for finding in findings]
    return header, rows


def render_report(findings, errors, users_scanned: int) -> str:
    """
    Renders the report-only output.
    :param findings: Findings returned by get_console_users.
    :param errors: Errors returned by get_console_users.
    :param users_scanned: Number of IAM users visited.
    :return: The complete report.
    """
    lines = [f'Scanned {users_scanned} IAM user(s); {len(findings)} have console '
             f'access (login profile).']
    if findings:
        lines.append('')
        header, rows = build_rows(findings)
        lines.extend(format_table(header, rows))
    for username, code in errors:
        lines.append(f'WARNING: could not read the login profile for user '
                     f'{username!r} ({code})')
    return '\n'.join(lines)


def summarize_removals(result: dict, apply: bool) -> list:
    """
    Builds the action lines and summary of a removal report.
    :param result: Return value of execute_removals.
    :param apply: Whether the removal was executed.
    :return: Report lines.
    """
    lines = []
    prefix = 'REMOVE CONSOLE ACCESS' if apply else 'WOULD REMOVE CONSOLE ACCESS'
    for entry in result['removed']:
        lines.append(f'{prefix}  {entry["username"]}')
    for entry in result['failed']:
        lines.append(f'FAILED  {entry["username"]}  ({entry["error"]})')

    removed = len(result['removed'])
    lead = 'Removed console access for' if apply else 'Would remove console access for'
    lines.append(f'{lead} {removed} user(s), skipped {len(result["skipped"])}, '
                 f'failed {len(result["failed"])}.')

    reasons = {}
    for entry in result['skipped']:
        reasons[entry['reason']] = reasons.get(entry['reason'], 0) + 1
    if reasons:
        breakdown = ', '.join(f'{reason} ({count})' for reason, count
                              in sorted(reasons.items(), key=lambda item: -item[1]))
        lines.append(f'Skipped: {breakdown}')
    return lines


def render_action_report(result: dict, errors, apply: bool,
                         users_scanned: int, findings_count: int) -> str:
    """
    Renders the human-readable report for a removal run.
    :param result: Return value of execute_removals.
    :param errors: Errors returned by get_console_users.
    :param apply: Whether the removal was executed.
    :param users_scanned: Number of IAM users visited.
    :param findings_count: Number of users that have console access.
    :return: The complete report.
    """
    mode = 'applied' if apply else 'dry run; pass --apply to execute'
    lines = [
        f'Scanned {users_scanned} IAM user(s); {findings_count} have console '
        f'access (login profile).',
        f'Mode: remove console access ({mode})',
        '',
    ]
    lines.extend(summarize_removals(result, apply))
    for username, code in errors:
        lines.append(f'WARNING: could not read the login profile for user '
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
    print(f'error: unable to list IAM users ({error_code})', file=sys.stderr)
    if error_code == 'InvalidClientTokenId':
        print('hint: this usually means the access key is invalid, deleted or '
              'deactivated; refresh the credentials and try again.',
              file=sys.stderr)
    return 2


def build_json_payload(findings, errors, users_scanned: int) -> str:
    """
    Builds the JSON report for a report-only run.
    :param findings: Findings returned by get_console_users.
    :param errors: Errors returned by get_console_users.
    :param users_scanned: Number of IAM users visited.
    :return: The JSON report.
    """
    payload = {
        'users_scanned': users_scanned,
        'count': len(findings),
        'console_access': findings,
        'errors': [{'username': username, 'error': code}
                   for username, code in errors],
    }
    return json.dumps(payload, indent=2)


def build_action_json_payload(result: dict, errors, apply: bool,
                              users_scanned: int, findings_count: int) -> str:
    """
    Builds the JSON report for a removal run.
    :param result: Return value of execute_removals.
    :param errors: Errors returned by get_console_users.
    :param apply: Whether the removal was executed.
    :param users_scanned: Number of IAM users visited.
    :param findings_count: Number of users that have console access.
    :return: The JSON report.
    """
    payload = {
        'users_scanned': users_scanned,
        'candidates': findings_count,
        'action': 'remove_console_access',
        'applied': apply,
        'removed': result['removed'],
        'skipped': result['skipped'],
        'failed': result['failed'],
        'errors': [{'username': username, 'error': code}
                   for username, code in errors],
    }
    return json.dumps(payload, indent=2)


def write_report(content: str, output_file, findings_count: int,
                 users_scanned: int) -> int:
    """
    Writes the report to a file, or to stdout when no file is configured.
    :param content: Report body.
    :param output_file: Destination path, or None for stdout.
    :param findings_count: Number of findings, used in the confirmation line.
    :param users_scanned: Number of IAM users visited.
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


def run_removal_mode(args, iam_client, session, findings, errors,
                     users_scanned) -> int:
    """
    Runs the removal phase and writes its report.
    :param args: Parsed arguments.
    :param iam_client: A boto3 IAM client.
    :param session: The boto3 session, used to identify the caller.
    :param findings: Findings returned by get_console_users.
    :param errors: Errors returned by get_console_users.
    :param users_scanned: Number of IAM users visited.
    :return: Process exit status.
    """
    caller_user = None if args.include_caller else caller_user_name(session)
    result = execute_removals(iam_client, findings, args.apply, caller_user,
                              excluded_users(args))

    if args.json:
        content = build_action_json_payload(result, errors, args.apply,
                                            users_scanned, len(findings))
    else:
        content = render_action_report(result, errors, args.apply,
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
    :param findings: Findings returned by get_console_users.
    :param errors: Errors returned by get_console_users.
    :param users_scanned: Number of IAM users visited.
    :return: Process exit status.
    """
    if args.json:
        content = build_json_payload(findings, errors, users_scanned)
    else:
        content = render_report(findings, errors, users_scanned)

    status = write_report(content, args.output_file, len(findings), users_scanned)
    if status:
        return status
    # An unreadable login profile means the report is incomplete: never report
    # success for a scan that could not answer for every user.
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
        findings, errors, users_scanned = get_console_users(iam_client)
    except NoCredentialsError:
        return report_scan_error()
    except ClientError as err:
        return report_scan_error(err.response.get('Error', {}).get('Code', 'unknown'))

    if args.remove:
        return run_removal_mode(args, iam_client, session, findings, errors,
                                users_scanned)
    return run_report_mode(args, findings, errors, users_scanned)


if __name__ == '__main__':
    sys.exit(main())
