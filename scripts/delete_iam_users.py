#!/usr/bin/env python3
"""
Report and delete IAM users that have been unused for a threshold number of days.

A user is selected when both are true:
  * the user was created more than N days ago (default 30), and
  * its last access is either never or more than N days ago.

"Last access" is the most recent of the console sign-in (PasswordLastUsed) and
every access key's LastUsedDate. A user with no console sign-in and no used key
counts as never used.

This script is standalone: it depends only on boto3 and imports nothing from
cloud_governance.

Deleting an IAM user is irreversible and requires removing everything attached to
it first. The script removes, in order: access keys, login profile, signing
certificates, SSH public keys, service-specific credentials, attached policies,
inline policies, group memberships and the permissions boundary, then calls
DeleteUser.

Safety rules:
  * report-only by default; deleting requires --delete and, to execute, --apply;
  * the caller's own user is never deleted, with no override;
  * a user with an MFA device is never deleted, because deactivating MFA needs an
    OTP code that this script cannot provide;
  * a user that has an access key or login profile created within N days is
    skipped as "recently provisioned" unless --force is given;
  * users in EXCLUDE_IAM_USERS or --exclude-user are never touched;
  * if last-access cannot be determined for a user, that user is not deleted.

Nothing else is checked: if a bucket or key policy references the user's ARN, that
reference is left behind.

Exit status: 1 when candidates exist or a user could not be inspected (report
mode), or when any deletion failed (action mode), 0 otherwise.

Examples:
    python scripts/delete_iam_users.py
    python scripts/delete_iam_users.py --days 90 --json
    python scripts/delete_iam_users.py --delete             # preview
    python scripts/delete_iam_users.py --delete --apply     # execute
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

DEFAULT_DAYS = 30
DEFAULT_REGION = 'us-east-1'
EXCLUDE_ENV_VAR = 'EXCLUDE_IAM_USERS'
MFA_REASON = 'has an MFA device (removing it requires an OTP)'


def parse_args(argv=None):
    """
    Parses the command line arguments.
    :param argv: Argument list (defaults to sys.argv[1:]).
    :return: Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description='Report or delete IAM users unused for more than N days.')
    parser.add_argument(
        '--days', type=int, default=DEFAULT_DAYS,
        help=f'Unused and created longer ago than this many days '
             f'(default: {DEFAULT_DAYS}).')
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
        '--delete', dest='action', action='store_true',
        help='Delete the selected users and everything attached to them. '
             'Irreversible. Dry run without --apply.')
    parser.add_argument(
        '--apply', action='store_true',
        help='Actually delete. Without it the deletion is only previewed.')
    parser.add_argument(
        '--force', action='store_true',
        help='Also select users that have an access key or login profile created '
             'within --days. The caller and MFA-protected users stay protected.')
    parser.add_argument(
        '--exclude-user', action='append', default=None, metavar='NAME',
        help=f'Never delete this IAM user. Repeatable. Prefer the '
             f'{EXCLUDE_ENV_VAR} environment variable (comma separated).')
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
    if args.days < 0:
        print('error: --days must be zero or greater', file=sys.stderr)
        return 2
    if args.apply and not args.action:
        print('error: --apply requires --delete', file=sys.stderr)
        return 2
    if args.force and not args.action:
        print('error: --force requires --delete', file=sys.stderr)
        return 2
    return 0


def excluded_users(args) -> set:
    """
    Collects the user names that must never be deleted, from the command line and
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
    Returns the IAM user name behind the credentials the script is running with.
    That user is never deleted.
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
    return arn.split(marker, 1)[1].rsplit('/', 1)[-1]


def format_date(value) -> str:
    """
    Formats an optional datetime returned by IAM.
    :param value: A datetime or None.
    :return: UTC timestamp, or 'never'.
    """
    return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else 'never'


def last_access_for_user(iam_client, user, access_keys):
    """
    Returns the most recent activity for a user: the later of the console sign-in
    and the last use of any access key.
    :param iam_client: A boto3 IAM client.
    :param user: A user entry from list_users.
    :param access_keys: The user's AccessKeyMetadata entries.
    :return: (datetime or None, error code or None). The datetime is None when the
        user was never used; an error code means last access could not be known.
    """
    last_access = user.get('PasswordLastUsed')
    for key in access_keys:
        try:
            response = iam_client.get_access_key_last_used(
                AccessKeyId=key['AccessKeyId'])
        except ClientError as err:
            return None, err.response.get('Error', {}).get('Code', 'unknown')
        used = response.get('AccessKeyLastUsed', {}).get('LastUsedDate')
        if used and (last_access is None or used > last_access):
            last_access = used
    return last_access, None


def recent_credential_blocker(iam_client, username, access_keys, days, now):
    """
    Detects credentials created within the threshold, which suggests the user is
    still being provisioned.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    :param access_keys: The user's AccessKeyMetadata entries.
    :param days: Threshold in days.
    :param now: Current time.
    :return: (blocked reason or None, error code or None).
    """
    threshold = timedelta(days=days)
    if any(now - key['CreateDate'] <= threshold for key in access_keys):
        return f'a credential was created within {days} days (use --force)', None
    try:
        profile = iam_client.get_login_profile(UserName=username)['LoginProfile']
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        if code == 'NoSuchEntity':
            return None, None
        return None, code
    if now - profile.get('CreateDate') <= threshold:
        return f'a credential was created within {days} days (use --force)', None
    return None, None


def blockers_for_user(iam_client, username, access_keys, days, force, now):
    """
    Collects the reasons a user must not be deleted.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    :param access_keys: The user's AccessKeyMetadata entries.
    :param days: Threshold in days.
    :param force: Whether recently provisioned users may be selected.
    :param now: Current time.
    :return: (list of reasons, error code or None).
    """
    reasons = []
    try:
        mfa_devices = iam_client.list_mfa_devices(
            UserName=username)['MFADevices']
    except ClientError as err:
        return [], err.response.get('Error', {}).get('Code', 'unknown')
    if mfa_devices:
        reasons.append(MFA_REASON)
    if not force:
        reason, error = recent_credential_blocker(
            iam_client, username, access_keys, days, now)
        if error:
            return [], error
        if reason:
            reasons.append(reason)
    return reasons, None


def inspect_user(iam_client, user, days, force, now):
    """
    Decides whether a single user is unused enough to be a candidate.
    :param iam_client: A boto3 IAM client.
    :param user: A user entry from list_users.
    :param days: Threshold in days.
    :param force: Whether recently provisioned users may be selected.
    :param now: Current time.
    :return: (finding or None, (username, error code) or None).
    """
    username = user['UserName']
    try:
        access_keys = iam_client.list_access_keys(
            UserName=username)['AccessKeyMetadata']
    except ClientError as err:
        return None, (username, err.response.get('Error', {}).get('Code', 'unknown'))

    last_access, error = last_access_for_user(iam_client, user, access_keys)
    if error:
        return None, (username, error)

    threshold = timedelta(days=days)
    if now - user['CreateDate'] <= threshold:
        return None, None
    if last_access is not None and now - last_access <= threshold:
        return None, None

    reasons, error = blockers_for_user(
        iam_client, username, access_keys, days, force, now)
    if error:
        return None, (username, error)

    finding = {
        'username': username,
        'created': format_date(user.get('CreateDate')),
        'age_days': (now - user['CreateDate']).days,
        'last_access': format_date(last_access),
        'last_access_days': (now - last_access).days if last_access else None,
        'access_keys': len(access_keys),
        'blocked_reason': '; '.join(reasons) if reasons else None,
    }
    return finding, None


def get_unused_users(iam_client, days: int, force: bool):
    """
    Lists every IAM user and collects those that are old and unused.
    :param iam_client: A boto3 IAM client.
    :param days: Threshold in days.
    :param force: Whether recently provisioned users may be selected.
    :return: (findings, errors, users_scanned).
    """
    now = datetime.now(timezone.utc)
    findings = []
    errors = []
    users_scanned = 0

    for page in iam_client.get_paginator('list_users').paginate():
        for user in page['Users']:
            users_scanned += 1
            finding, error = inspect_user(iam_client, user, days, force, now)
            if error:
                errors.append(error)
            elif finding:
                findings.append(finding)

    findings.sort(key=lambda finding: finding['username'].lower())
    return findings, errors, users_scanned


def _delete_access_keys(iam_client, username: str):
    """
    Deletes every access key of the user.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for key in iam_client.list_access_keys(
            UserName=username)['AccessKeyMetadata']:
        iam_client.delete_access_key(
            UserName=username, AccessKeyId=key['AccessKeyId'])


def _delete_login_profile(iam_client, username: str):
    """
    Deletes the user's login profile, ignoring the case where none exists.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    try:
        iam_client.delete_login_profile(UserName=username)
    except ClientError as err:
        if err.response.get('Error', {}).get('Code') != 'NoSuchEntity':
            raise


def _delete_signing_certificates(iam_client, username: str):
    """
    Deletes the user's signing certificates.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for cert in iam_client.list_signing_certificates(
            UserName=username)['Certificates']:
        iam_client.delete_signing_certificate(
            UserName=username, CertificateId=cert['CertificateId'])


def _delete_ssh_public_keys(iam_client, username: str):
    """
    Deletes the user's SSH public keys.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for ssh_key in iam_client.list_ssh_public_keys(
            UserName=username)['SSHPublicKeys']:
        iam_client.delete_ssh_public_key(
            UserName=username, SSHPublicKeyId=ssh_key['SSHPublicKeyId'])


def _delete_service_specific_credentials(iam_client, username: str):
    """
    Deletes the user's service-specific credentials (for example CodeCommit).
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for credential in iam_client.list_service_specific_credentials(
            UserName=username)['ServiceSpecificCredentials']:
        iam_client.delete_service_specific_credential(
            UserName=username,
            ServiceSpecificCredentialId=credential['ServiceSpecificCredentialId'])


def _detach_attached_policies(iam_client, username: str):
    """
    Detaches every managed policy attached to the user.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for policy in iam_client.list_attached_user_policies(
            UserName=username)['AttachedPolicies']:
        iam_client.detach_user_policy(
            UserName=username, PolicyArn=policy['PolicyArn'])


def _delete_inline_policies(iam_client, username: str):
    """
    Deletes every inline policy of the user.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for policy_name in iam_client.list_user_policies(
            UserName=username)['PolicyNames']:
        iam_client.delete_user_policy(
            UserName=username, PolicyName=policy_name)


def _leave_groups(iam_client, username: str):
    """
    Removes the user from every group.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    for group in iam_client.list_groups_for_user(UserName=username)['Groups']:
        iam_client.remove_user_from_group(
            GroupName=group['GroupName'], UserName=username)


def _delete_permissions_boundary(iam_client, username: str):
    """
    Deletes the user's permissions boundary when one is set.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    """
    user = iam_client.get_user(UserName=username)['User']
    if user.get('PermissionsBoundary'):
        iam_client.delete_user_permissions_boundary(UserName=username)


def delete_user_account(iam_client, username: str):
    """
    Removes everything attached to the user, then deletes the user.
    MFA devices are not removed here: their deactivation needs an OTP code, so
    such users are filtered out before this is called.
    :param iam_client: A boto3 IAM client.
    :param username: IAM user name.
    :return: None on success, otherwise the AWS error code.
    """
    try:
        _delete_access_keys(iam_client, username)
        _delete_login_profile(iam_client, username)
        _delete_signing_certificates(iam_client, username)
        _delete_ssh_public_keys(iam_client, username)
        _delete_service_specific_credentials(iam_client, username)
        _detach_attached_policies(iam_client, username)
        _delete_inline_policies(iam_client, username)
        _leave_groups(iam_client, username)
        _delete_permissions_boundary(iam_client, username)
        iam_client.delete_user(UserName=username)
    except ClientError as err:
        return err.response.get('Error', {}).get('Code', 'unknown')
    return None


def skip_reason(finding, caller_user, excluded: set):
    """
    Decides whether a candidate must be left alone, and why.
    :param finding: One entry from get_unused_users.
    :param caller_user: The caller's own IAM user name, or None.
    :param excluded: User names that must never be deleted.
    :return: A human-readable reason, or None when the user may be deleted.
    """
    if caller_user and finding['username'] == caller_user:
        return "caller's own user"
    if finding['username'] in excluded:
        return 'excluded by --exclude-user'
    if finding['blocked_reason']:
        return finding['blocked_reason']
    return None


def execute_deletions(iam_client, findings, apply: bool, caller_user,
                      excluded: set) -> dict:
    """
    Walks the findings and deletes eligible users when apply is True.
    :param iam_client: A boto3 IAM client.
    :param findings: Findings returned by get_unused_users.
    :param apply: Whether to actually delete.
    :param caller_user: The caller's own IAM user name, or None.
    :param excluded: User names that must never be deleted.
    :return: dict with 'deleted', 'skipped' and 'failed' lists.
    """
    deleted, skipped, failed = [], [], []
    for finding in findings:
        reason = skip_reason(finding, caller_user, excluded)
        if reason:
            skipped.append({**finding, 'reason': reason})
            continue
        if apply:
            error_code = delete_user_account(iam_client, finding['username'])
            if error_code == 'NoSuchEntity':
                skipped.append({**finding, 'reason': 'already absent'})
                continue
            if error_code:
                failed.append({**finding, 'error': error_code})
                continue
        deleted.append(dict(finding))
    return {'deleted': deleted, 'skipped': skipped, 'failed': failed}


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
    :param findings: Findings returned by get_unused_users.
    :return: (header, rows) as lists of strings.
    """
    header = ['USER', 'CREATED (UTC)', 'AGE (DAYS)', 'LAST ACCESS (UTC)',
              'LAST ACCESS DAYS', 'KEYS', 'STATUS']
    rows = [[finding['username'], finding['created'], str(finding['age_days']),
             finding['last_access'],
             'never' if finding['last_access_days'] is None
             else str(finding['last_access_days']),
             str(finding['access_keys']),
             finding['blocked_reason'] or 'eligible']
            for finding in findings]
    return header, rows


def render_report(findings, errors, days: int, users_scanned: int) -> str:
    """
    Renders the report-only output.
    :param findings: Findings returned by get_unused_users.
    :param errors: Errors returned by get_unused_users.
    :param days: Threshold used for the summary line.
    :param users_scanned: Number of IAM users visited.
    :return: The complete report.
    """
    eligible = sum(1 for finding in findings if not finding['blocked_reason'])
    lines = [f'Scanned {users_scanned} IAM user(s); {len(findings)} unused and '
             f'older than {days} day(s), {eligible} eligible for deletion.']
    if findings:
        lines.append('')
        header, rows = build_rows(findings)
        lines.extend(format_table(header, rows))
    for username, code in errors:
        lines.append(f'WARNING: could not inspect user {username!r} ({code}); '
                     f'it will not be deleted')
    return '\n'.join(lines)


def summarize_deletions(result: dict, apply: bool) -> list:
    """
    Builds the action lines and summary of a deletion report.
    :param result: Return value of execute_deletions.
    :param apply: Whether the deletion was executed.
    :return: Report lines.
    """
    lines = []
    prefix = 'DELETE' if apply else 'WOULD DELETE'
    for entry in result['deleted']:
        last_access = ('never' if entry['last_access_days'] is None
                       else f'{entry["last_access_days"]}d ago')
        lines.append(f'{prefix}  {entry["username"]}  (created '
                     f'{entry["age_days"]}d ago, last access {last_access})')
    for entry in result['failed']:
        lines.append(f'FAILED  {entry["username"]}  ({entry["error"]})')

    count = len(result['deleted'])
    lead = 'Deleted' if apply else 'Would delete'
    lines.append(f'{lead} {count} user(s), skipped {len(result["skipped"])}, '
                 f'failed {len(result["failed"])}.')

    reasons = {}
    for entry in result['skipped']:
        reasons[entry['reason']] = reasons.get(entry['reason'], 0) + 1
    if reasons:
        breakdown = ', '.join(f'{reason} ({count})' for reason, count
                              in sorted(reasons.items(), key=lambda item: -item[1]))
        lines.append(f'Skipped: {breakdown}')
    return lines


def render_action_report(result: dict, errors, apply: bool, days: int,
                         users_scanned: int, findings_count: int) -> str:
    """
    Renders the human-readable report for a deletion run.
    :param result: Return value of execute_deletions.
    :param errors: Errors returned by get_unused_users.
    :param apply: Whether the deletion was executed.
    :param days: Threshold used for the summary line.
    :param users_scanned: Number of IAM users visited.
    :param findings_count: Number of candidate users.
    :return: The complete report.
    """
    mode = 'applied' if apply else 'dry run; pass --apply to execute'
    lines = [
        f'Scanned {users_scanned} IAM user(s); {findings_count} unused and '
        f'older than {days} day(s).',
        f'Mode: delete IAM user ({mode})',
        '',
    ]
    lines.extend(summarize_deletions(result, apply))
    for username, code in errors:
        lines.append(f'WARNING: could not inspect user {username!r} ({code})')
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


def build_json_payload(findings, errors, days: int, users_scanned: int) -> str:
    """
    Builds the JSON report for a report-only run.
    :param findings: Findings returned by get_unused_users.
    :param errors: Errors returned by get_unused_users.
    :param days: Threshold used for the scan.
    :param users_scanned: Number of IAM users visited.
    :return: The JSON report.
    """
    payload = {
        'threshold_days': days,
        'users_scanned': users_scanned,
        'count': len(findings),
        'candidates': findings,
        'errors': [{'username': username, 'error': code}
                   for username, code in errors],
    }
    return json.dumps(payload, indent=2)


def build_action_json_payload(result: dict, errors, apply: bool, days: int,
                              users_scanned: int, findings_count: int) -> str:
    """
    Builds the JSON report for a deletion run.
    :param result: Return value of execute_deletions.
    :param errors: Errors returned by get_unused_users.
    :param apply: Whether the deletion was executed.
    :param days: Threshold used for the scan.
    :param users_scanned: Number of IAM users visited.
    :param findings_count: Number of candidate users.
    :return: The JSON report.
    """
    payload = {
        'threshold_days': days,
        'users_scanned': users_scanned,
        'candidates': findings_count,
        'action': 'delete_iam_user',
        'applied': apply,
        'deleted': result['deleted'],
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


def run_delete_mode(args, iam_client, session, findings, errors,
                    users_scanned) -> int:
    """
    Runs the deletion phase and writes its report.
    :param args: Parsed arguments.
    :param iam_client: A boto3 IAM client.
    :param session: The boto3 session, used to identify the caller.
    :param findings: Findings returned by get_unused_users.
    :param errors: Errors returned by get_unused_users.
    :param users_scanned: Number of IAM users visited.
    :return: Process exit status.
    """
    result = execute_deletions(iam_client, findings, args.apply,
                               caller_user_name(session), excluded_users(args))

    if args.json:
        content = build_action_json_payload(result, errors, args.apply, args.days,
                                            users_scanned, len(findings))
    else:
        content = render_action_report(result, errors, args.apply, args.days,
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
    :param findings: Findings returned by get_unused_users.
    :param errors: Errors returned by get_unused_users.
    :param users_scanned: Number of IAM users visited.
    :return: Process exit status.
    """
    if args.json:
        content = build_json_payload(findings, errors, args.days, users_scanned)
    else:
        content = render_report(findings, errors, args.days, users_scanned)

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
        findings, errors, users_scanned = get_unused_users(
            iam_client, args.days, args.force)
    except NoCredentialsError:
        return report_scan_error()
    except ClientError as err:
        return report_scan_error(err.response.get('Error', {}).get('Code', 'unknown'))

    if args.action:
        return run_delete_mode(args, iam_client, session, findings, errors,
                               users_scanned)
    return run_report_mode(args, findings, errors, users_scanned)


if __name__ == '__main__':
    sys.exit(main())
