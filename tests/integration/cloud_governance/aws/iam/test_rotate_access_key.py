"""
Integration tests for the rotate_access_key policy against a real AWS account.

Nothing runs unless IAM_ROTATE_INTEGRATION=yes, so CI and normal pytest runs are unaffected.

The temp-user test creates and cleans up its own IAM user, so it is safe to run:

    IAM_ROTATE_INTEGRATION=yes \
        python -m pytest tests/integration/cloud_governance/aws/iam/test_rotate_access_key.py \
        -k test_rotate_access_key_end_to_end_with_temp_user -v -s

The real-user test consumes the user's inactive access key and requires explicit opt-in.
It targets the same `username` variable the policy uses:

    IAM_ROTATE_INTEGRATION=yes username=<iam-user> IAM_ROTATE_TEST_CONFIRM=yes \
        python -m pytest tests/integration/cloud_governance/aws/iam/test_rotate_access_key.py \
        -k test_rotate_real_user -v -s
"""
import json
import os
import stat
import time
import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.rotate_access_key import RotateAccessKey, _ROTATED_USERS

REAL_USER = os.environ.get('username', '')
REAL_USER_CONFIRMED = os.environ.get('IAM_ROTATE_TEST_CONFIRM', '').lower() == 'yes'
AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

pytestmark = pytest.mark.skipif(
    os.environ.get('IAM_ROTATE_INTEGRATION', '').lower() != 'yes',
    reason='set IAM_ROTATE_INTEGRATION=yes to run against a real AWS account')


def _set_environment_variables(username: str, credentials_file, dry_run: str = 'no'):
    environment_variables.environment_variables_dict['policy'] = 'rotate_access_key'
    environment_variables.environment_variables_dict['username'] = username
    environment_variables.environment_variables_dict['dry_run'] = dry_run
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = str(credentials_file)


def _reset_environment_variables():
    _ROTATED_USERS.clear()
    environment_variables.environment_variables_dict['username'] = ''
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = ''


def _get_inactive_key_ids(iam_client, username: str) -> list:
    keys = iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']
    return [key['AccessKeyId'] for key in keys if key['Status'] == 'Inactive']


def _assert_credentials_work(payload: dict, username: str, attempts: int = 4, delay: int = 3):
    """Proves the returned secret is a usable credential for the rotated user."""
    # Use a Session rather than boto3.client(aws_access_key_id=...): passing keys to client()
    # still lets botocore pick up AWS_SESSION_TOKEN from the environment, which makes the request
    # invalid when the caller authenticated with temporary credentials.
    session = boto3.Session(
        aws_access_key_id=payload['access_key_id'],
        aws_secret_access_key=payload['secret_access_key'],
        region_name=AWS_DEFAULT_REGION,
    )
    last_error = None
    for attempt in range(attempts):
        try:
            identity = session.client('sts').get_caller_identity()
        except ClientError as err:
            # A brand new access key can take a moment to propagate through STS.
            if err.response.get('Error', {}).get('Code') != 'InvalidClientTokenId':
                raise
            last_error = err
            if attempt + 1 < attempts:
                time.sleep(delay)
            continue
        # Raised explicitly: a bare assert would make pytest print the ARN, which contains
        # the account id, in the failure output.
        if not identity.get('Arn', '').endswith(f'user/{username}'):
            raise AssertionError("the new access key does not authenticate as the requested user")
        return
    raise AssertionError(
        f"The newly created access key is not accepted by STS after "
        f"{attempts} attempts: {last_error}. Check that the key is still Active "
        f"(list_access_keys) and that no AWS_SESSION_TOKEN/AWS_PROFILE leaks into the environment."
    )


def _assert_rotation(iam_client, username: str, old_key_id: str, credentials_file):
    metadata = {key['AccessKeyId']: key
                for key in iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']}
    # The key-id assertions below are raised explicitly: a bare assert would make pytest
    # print the access key id in the failure output.
    if old_key_id in metadata:
        raise AssertionError("the inactive access key was not deleted")

    payload = json.loads(credentials_file.read_text())
    if payload['username'] != username:
        raise AssertionError("the credentials file does not belong to the requested user")
    if payload['access_key_id'] not in metadata:
        raise AssertionError("the newly created access key was not found in IAM")
    assert payload['secret_access_key']
    if metadata[payload['access_key_id']]['Status'] != 'Active':
        raise AssertionError("the newly created access key is not Active")
    assert stat.S_IMODE(os.stat(credentials_file).st_mode) == 0o600
    _assert_credentials_work(payload, username)


@pytest.mark.skipif(not REAL_USER, reason='set username=<iam-user> to run against a real account')
def test_rotate_real_user(tmp_path):
    if not REAL_USER_CONFIRMED:
        pytest.skip('set IAM_ROTATE_TEST_CONFIRM=yes to rotate a key on a real IAM user')

    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    inactive_key_ids = _get_inactive_key_ids(iam_client, REAL_USER)
    if not inactive_key_ids:
        pytest.skip("the requested user has no inactive access key")

    old_key_id = inactive_key_ids[0]
    credentials_file = tmp_path / 'creds.json'
    try:
        _reset_environment_variables()
        _set_environment_variables(REAL_USER, credentials_file, dry_run='no')

        result = RotateAccessKey().run_policy_operations()

        assert len(result) == 1
        _assert_rotation(iam_client, REAL_USER, old_key_id, credentials_file)
    finally:
        _reset_environment_variables()


def test_rotate_access_key_end_to_end_with_temp_user(tmp_path):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    username = f'integration-rotate-{uuid.uuid4().hex[:12]}'
    credentials_file = tmp_path / 'creds.json'
    try:
        iam_client.create_user(UserName=username, Tags=[{'Key': 'User', 'Value': 'integration'}])
        old_key_id = iam_client.create_access_key(UserName=username)['AccessKey']['AccessKeyId']
        iam_client.update_access_key(UserName=username, AccessKeyId=old_key_id, Status='Inactive')

        _reset_environment_variables()
        _set_environment_variables(username, credentials_file, dry_run='no')

        result = RotateAccessKey().run_policy_operations()

        assert len(result) == 1
        assert result[0]['ResourceAction'] == 'True'
        _assert_rotation(iam_client, username, old_key_id, credentials_file)
    finally:
        _reset_environment_variables()
        try:
            for key in iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']:
                iam_client.delete_access_key(UserName=username, AccessKeyId=key['AccessKeyId'])
            iam_client.delete_user(UserName=username)
        except Exception:
            pass
