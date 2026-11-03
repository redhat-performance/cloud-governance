"""
Unit tests for cloud_governance.policy.aws.rotate_access_key.RotateAccessKey.
"""
import json
import os
import stat

import boto3
import pytest
from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.rotate_access_key import RotateAccessKey, _ROTATED_USERS
from tests.unittest.configs import DRY_RUN_YES, DRY_RUN_NO, AWS_DEFAULT_REGION, TEST_USER_NAME


@pytest.fixture(autouse=True)
def reset_rotated_users():
    """The process-wide guard must not leak between tests."""
    _ROTATED_USERS.clear()
    yield
    _ROTATED_USERS.clear()


def _set_environment_variables(credentials_file, username=TEST_USER_NAME, dry_run=DRY_RUN_YES):
    environment_variables.environment_variables_dict['policy'] = 'rotate_access_key'
    environment_variables.environment_variables_dict['username'] = username
    environment_variables.environment_variables_dict['dry_run'] = dry_run
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = str(credentials_file)


def _create_user_with_inactive_key(tags: list = None):
    """Create a moto IAM user with one inactive access key."""
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    create_kwargs = {'UserName': TEST_USER_NAME}
    if tags:
        create_kwargs['Tags'] = tags
    iam_client.create_user(**create_kwargs)
    access_key_id = iam_client.create_access_key(UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId']
    iam_client.update_access_key(UserName=TEST_USER_NAME, AccessKeyId=access_key_id, Status='Inactive')
    return iam_client, access_key_id


def _add_inactive_key(iam_client):
    access_key_id = iam_client.create_access_key(UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId']
    iam_client.update_access_key(UserName=TEST_USER_NAME, AccessKeyId=access_key_id, Status='Inactive')
    return access_key_id


@mock_aws
def test_rotate_access_key_skips_without_username(tmp_path):
    _set_environment_variables(tmp_path / 'creds.json', username='')

    assert RotateAccessKey().run_policy_operations() == []


@mock_aws
def test_rotate_access_key_skips_when_no_inactive_key(tmp_path):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=TEST_USER_NAME)
    iam_client.create_access_key(UserName=TEST_USER_NAME)
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    assert RotateAccessKey().run_policy_operations() == []
    assert not credentials_file.exists()


@mock_aws
def test_rotate_access_key_honors_skip_tag(tmp_path):
    _create_user_with_inactive_key(tags=[{'Key': 'Policy', 'Value': 'notdelete'}])
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    assert RotateAccessKey().run_policy_operations() == []
    assert not credentials_file.exists()


@mock_aws
def test_rotate_access_key_dry_run_reports_without_rotating(tmp_path):
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_YES)

    result = RotateAccessKey().run_policy_operations()

    assert len(result) == 1
    assert result[0]['ResourceId'] == TEST_USER_NAME
    assert result[0]['ResourceType'] == 'AccessKeyRotation'
    assert result[0]['ResourceAction'] == 'False'
    assert not credentials_file.exists()
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [inactive_key_id]


@mock_aws
def test_rotate_access_key_replaces_inactive_key_and_writes_credentials(tmp_path):
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    result = RotateAccessKey().run_policy_operations()

    assert len(result) == 1
    assert result[0]['ResourceType'] == 'AccessKeyRotation'
    assert result[0]['ResourceAction'] == 'True'
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert len(keys) == 1
    new_key_id = keys[0]['AccessKeyId']
    assert new_key_id != inactive_key_id
    assert keys[0]['Status'] == 'Active'

    payload = json.loads(credentials_file.read_text())
    assert payload['username'] == TEST_USER_NAME
    assert payload['access_key_id'] == new_key_id
    assert payload['secret_access_key']
    assert stat.S_IMODE(os.stat(credentials_file).st_mode) == 0o600


@mock_aws
def test_rotate_access_key_rotates_only_once_per_process(tmp_path):
    iam_client, _ = _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    policy = RotateAccessKey()
    assert len(policy.run_policy_operations()) == 1

    # A second region in the same process must not rotate the next inactive key.
    remaining_inactive_key_id = _add_inactive_key(iam_client)
    assert policy.run_policy_operations() == []
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert remaining_inactive_key_id in [key['AccessKeyId'] for key in keys]
