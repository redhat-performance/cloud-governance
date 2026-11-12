"""
Unit tests for IAMOperations access key rotation.
"""
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations

AWS_DEFAULT_REGION = 'us-east-1'
USER_NAME = 'unit-test-rotate'


def _create_user_with_inactive_key():
    """
    Creates a moto IAM user with one inactive access key.
    :return: (iam_client, access_key_id)
    """
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    access_key_id = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']
    iam_client.update_access_key(UserName=USER_NAME, AccessKeyId=access_key_id, Status='Inactive')
    return iam_client, access_key_id


@mock_aws
def test_get_inactive_access_keys_returns_only_inactive_keys():
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    active_key_id = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']

    inactive_keys = IAMOperations(iam_client=iam_client).get_inactive_access_keys(USER_NAME)

    assert [key['AccessKeyId'] for key in inactive_keys] == [inactive_key_id]
    assert active_key_id not in [key['AccessKeyId'] for key in inactive_keys]


@mock_aws
def test_get_inactive_access_keys_returns_empty_list_for_unknown_user():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    assert IAMOperations(iam_client=iam_client).get_inactive_access_keys('missing-user') == []


@mock_aws
def test_rotate_user_access_key_deletes_inactive_key_and_creates_new_one():
    iam_client, inactive_key_id = _create_user_with_inactive_key()

    credentials = IAMOperations(iam_client=iam_client).rotate_user_access_key(USER_NAME)

    assert credentials is not None
    new_key_id, new_secret = credentials
    assert new_key_id != inactive_key_id
    assert new_secret

    keys = iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [new_key_id]
    assert keys[0]['Status'] == 'Active'


@mock_aws
def test_rotate_user_access_key_returns_none_without_inactive_key():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    active_key_id = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']

    assert IAMOperations(iam_client=iam_client).rotate_user_access_key(USER_NAME) is None

    keys = iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [active_key_id]


@mock_aws
def test_rotate_user_access_key_raises_when_create_fails_after_delete():
    iam_client, inactive_key_id = _create_user_with_inactive_key()

    with patch.object(iam_client, 'create_access_key', side_effect=Exception('boom')):
        with pytest.raises(RuntimeError):
            IAMOperations(iam_client=iam_client).rotate_user_access_key(USER_NAME)

    # Delete-then-create means the old key is already gone; surface that loudly.
    assert iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata'] == []


@mock_aws
def test_rotate_user_access_key_dry_run_changes_nothing():
    iam_client, inactive_key_id = _create_user_with_inactive_key()

    assert IAMOperations(iam_client=iam_client).rotate_user_access_key(USER_NAME, dry_run=True) is None

    keys = iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [inactive_key_id]
    assert keys[0]['Status'] == 'Inactive'


@mock_aws
def test_has_free_access_key_slot_tracks_the_two_key_limit():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    operations = IAMOperations(iam_client=iam_client)

    assert operations.has_free_access_key_slot(USER_NAME) is True
    iam_client.create_access_key(UserName=USER_NAME)
    assert operations.has_free_access_key_slot(USER_NAME) is True
    iam_client.create_access_key(UserName=USER_NAME)
    assert operations.has_free_access_key_slot(USER_NAME) is False


@mock_aws
def test_has_free_access_key_slot_is_false_for_unknown_user():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)

    assert IAMOperations(iam_client=iam_client).has_free_access_key_slot('missing-user') is False


@mock_aws
def test_create_user_access_key_keeps_the_existing_key():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    existing_key_id = iam_client.create_access_key(
        UserName=USER_NAME)['AccessKey']['AccessKeyId']

    credentials = IAMOperations(iam_client=iam_client).create_user_access_key(USER_NAME)

    assert credentials is not None
    new_key_id, new_secret = credentials
    assert new_key_id != existing_key_id
    assert new_secret
    keys = iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']
    assert {key['AccessKeyId']: key['Status'] for key in keys} == {
        existing_key_id: 'Active', new_key_id: 'Active'}


@mock_aws
def test_create_user_access_key_dry_run_creates_nothing():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    existing_key_id = iam_client.create_access_key(
        UserName=USER_NAME)['AccessKey']['AccessKeyId']

    assert IAMOperations(iam_client=iam_client).create_user_access_key(
        USER_NAME, dry_run=True) is None

    keys = iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [existing_key_id]


NEW_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'
NEW_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'


def _create_user_with_two_active_keys():
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=USER_NAME)
    first = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']
    second = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']
    return iam_client, first, second


def _key_statuses(iam_client):
    return {key['AccessKeyId']: key['Status']
            for key in iam_client.list_access_keys(UserName=USER_NAME)['AccessKeyMetadata']}


@mock_aws
def test_deactivate_access_key_with_credentials_inactivates_the_target_key():
    iam_client, first, second = _create_user_with_two_active_keys()

    IAMOperations(iam_client=iam_client).deactivate_access_key_with_credentials(
        username=USER_NAME, access_key_id=first,
        aws_access_key_id=NEW_ACCESS_KEY_ID, aws_secret_access_key=NEW_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION)

    statuses = _key_statuses(iam_client)
    assert statuses[first] == 'Inactive'
    assert statuses[second] == 'Active'


@mock_aws
def test_deactivate_access_key_with_credentials_raises_when_the_key_was_deleted():
    # A missing key means the rotation consumed the key stored in Jenkins instead of it being
    # deactivated; that is a setup error, not success.
    iam_client, first, second = _create_user_with_two_active_keys()

    with pytest.raises(RuntimeError) as error:
        IAMOperations(iam_client=iam_client).deactivate_access_key_with_credentials(
            username=USER_NAME, access_key_id='AKIACONSUMEDEXAMPLE',
            aws_access_key_id=NEW_ACCESS_KEY_ID, aws_secret_access_key=NEW_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION)

    assert 'no longer exists' in str(error.value)
    statuses = _key_statuses(iam_client)
    assert statuses == {first: 'Active', second: 'Active'}


@mock_aws
def test_deactivate_stale_active_keys_keeps_only_the_published_key():
    iam_client, keep_key, stale_key = _create_user_with_two_active_keys()

    deactivated = IAMOperations(iam_client=iam_client).deactivate_stale_active_keys(
        username=USER_NAME, keep_access_key_id=keep_key,
        aws_access_key_id=NEW_ACCESS_KEY_ID, aws_secret_access_key=NEW_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION)

    assert deactivated == 1
    statuses = _key_statuses(iam_client)
    assert statuses[keep_key] == 'Active'
    assert statuses[stale_key] == 'Inactive'


@mock_aws
def test_deactivate_stale_active_keys_never_deactivates_the_caller_key(monkeypatch):
    iam_client, keep_key, caller_key = _create_user_with_two_active_keys()
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', caller_key)

    deactivated = IAMOperations(iam_client=iam_client).deactivate_stale_active_keys(
        username=USER_NAME, keep_access_key_id=keep_key,
        aws_access_key_id=NEW_ACCESS_KEY_ID, aws_secret_access_key=NEW_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION)

    assert deactivated == 0
    assert _key_statuses(iam_client)[caller_key] == 'Active'


@mock_aws
def test_deactivate_stale_active_keys_ignores_inactive_keys():
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    keep_key = iam_client.create_access_key(UserName=USER_NAME)['AccessKey']['AccessKeyId']

    deactivated = IAMOperations(iam_client=iam_client).deactivate_stale_active_keys(
        username=USER_NAME, keep_access_key_id=keep_key,
        aws_access_key_id=NEW_ACCESS_KEY_ID, aws_secret_access_key=NEW_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION)

    assert deactivated == 0
    assert _key_statuses(iam_client)[inactive_key_id] == 'Inactive'
