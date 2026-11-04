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
