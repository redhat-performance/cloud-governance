"""
Unit tests for cloud_governance.policy.aws.rotate_access_key.RotateAccessKey.
"""
import json
import logging
import os
import stat
from types import SimpleNamespace

import boto3
from botocore.exceptions import ClientError
import pytest
from moto import mock_aws

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws import rotate_access_key as rotate_access_key_module
from cloud_governance.policy.aws.rotate_access_key import RotateAccessKey, _ROTATED_USERS
from tests.unittest.configs import DRY_RUN_YES, DRY_RUN_NO, AWS_DEFAULT_REGION, TEST_USER_NAME


@pytest.fixture(autouse=True)
def reset_rotated_users():
    """The process-wide guard must not leak between tests."""
    _ROTATED_USERS.clear()
    yield
    _ROTATED_USERS.clear()


def _set_environment_variables(credentials_file, username=TEST_USER_NAME, dry_run=DRY_RUN_YES,
                               publish_to_jenkins=False):
    environment_variables.environment_variables_dict['policy'] = 'rotate_access_key'
    environment_variables.environment_variables_dict['username'] = username
    environment_variables.environment_variables_dict['dry_run'] = dry_run
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = str(credentials_file)
    environment_variables.environment_variables_dict['IAM_PUBLISH_TO_JENKINS'] = publish_to_jenkins


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
def test_rotate_access_key_creates_a_key_directly_when_a_slot_is_free(tmp_path):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=TEST_USER_NAME)
    active_key_id = iam_client.create_access_key(
        UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId']
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    result = RotateAccessKey().run_policy_operations()

    assert len(result) == 1
    assert result[0]['ResourceAction'] == 'True'
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    statuses = {key['AccessKeyId']: key['Status'] for key in keys}
    # The existing key is untouched; the new key is created in the free slot.
    assert len(keys) == 2
    assert statuses[active_key_id] == 'Active'
    new_key_ids = [key_id for key_id in statuses if key_id != active_key_id]
    assert len(new_key_ids) == 1
    assert statuses[new_key_ids[0]] == 'Active'
    payload = json.loads(credentials_file.read_text())
    assert payload['access_key_id'] == new_key_ids[0]
    assert payload['secret_access_key']


@mock_aws
def test_rotate_access_key_skips_without_inactive_key_or_free_slot(tmp_path):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=TEST_USER_NAME)
    key_ids = [iam_client.create_access_key(
        UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId'] for _ in range(2)]
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    assert RotateAccessKey().run_policy_operations() == []
    assert not credentials_file.exists()
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == key_ids


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
def test_rotate_access_key_refuses_to_rotate_without_a_destination():
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    # No Jenkins publish and no explicit file: there is nowhere to deliver the new secret.
    _set_environment_variables('', dry_run=DRY_RUN_NO)

    assert RotateAccessKey().run_policy_operations() == []

    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [inactive_key_id]


@mock_aws
def test_rotate_access_key_dry_run_works_without_a_destination():
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    _set_environment_variables('', dry_run=DRY_RUN_YES)

    result = RotateAccessKey().run_policy_operations()

    assert result[0]['ResourceAction'] == 'False'
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [inactive_key_id]


@mock_aws
def test_rotate_access_key_logs_connection_with_new_key(tmp_path, caplog):
    _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO)

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        RotateAccessKey().run_policy_operations()

    assert any('Successfully connected to AWS with the newly created access key' in record.message
               for record in caplog.records), [record.message for record in caplog.records]


class _FlakySts:
    """STS client that rejects the first `failures` calls as not-yet-propagated."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def get_caller_identity(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise ClientError({'Error': {'Code': 'InvalidClientTokenId', 'Message': 'invalid token'}},
                              'GetCallerIdentity')
        return {'Account': '123456789012', 'Arn': f'arn:aws:iam::123456789012:user/{TEST_USER_NAME}'}


def _patch_sts(monkeypatch, sts: _FlakySts):
    monkeypatch.setattr(rotate_access_key_module.boto3, 'Session',
                        lambda **kwargs: SimpleNamespace(client=lambda name: sts))
    monkeypatch.setattr(rotate_access_key_module.time, 'sleep', lambda seconds: None)


def _bare_policy() -> RotateAccessKey:
    """Skip AWSPolicyOperations.__init__: the connectivity check only needs the region."""
    policy = RotateAccessKey.__new__(RotateAccessKey)
    policy._region = AWS_DEFAULT_REGION
    return policy


def test_log_new_key_connectivity_retries_until_key_propagates(monkeypatch, caplog):
    sts = _FlakySts(failures=2)
    _patch_sts(monkeypatch, sts)

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        _bare_policy()._log_new_key_connectivity('AKIATESTKEY', 'secret')

    assert sts.calls == 3
    assert any('Successfully connected to AWS with the newly created access key' in record.message
               for record in caplog.records)


def test_log_new_key_connectivity_warns_when_key_never_propagates(monkeypatch, caplog):
    sts = _FlakySts(failures=RotateAccessKey.VERIFY_ATTEMPTS + 10)
    _patch_sts(monkeypatch, sts)

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        _bare_policy()._log_new_key_connectivity('AKIATESTKEY', 'secret')

    assert sts.calls == RotateAccessKey.VERIFY_ATTEMPTS
    assert any('was not accepted by STS' in record.message for record in caplog.records)


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


@mock_aws
def test_rotate_access_key_publishes_to_jenkins_when_enabled(tmp_path, monkeypatch):
    iam_client, _ = _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO, publish_to_jenkins=True)
    calls = {}

    class _FakeJenkins:
        @staticmethod
        def read_secret(credentials_id):
            return 'AKIAOLDKEY'

    def fake_preconditions(iam_operations, username, jenkins_access_key_id):
        calls['preconditions'] = (iam_operations, username, jenkins_access_key_id)

    def fake_publish(credentials, client, **kwargs):
        calls['publish'] = (credentials, kwargs)
        return {'username': TEST_USER_NAME, 'access_key_to_inactive': 'AKIAOLDKEY'}

    monkeypatch.setattr(rotate_access_key_module, 'get_jenkins_client', lambda: _FakeJenkins())
    monkeypatch.setattr(rotate_access_key_module, 'ensure_rotation_preconditions',
                        fake_preconditions)
    monkeypatch.setattr(rotate_access_key_module, 'rotate_and_publish_credentials', fake_publish)

    policy = RotateAccessKey()
    result = policy.run_policy_operations()

    assert result[0]['ResourceAction'] == 'True'
    assert calls['preconditions'] == (policy._iam_operations, TEST_USER_NAME, 'AKIAOLDKEY')
    published = calls['publish'][0]
    assert published['username'] == TEST_USER_NAME
    assert published['secret_access_key']
    assert published['access_key_id']
    assert calls['publish'][1]['region_name'] == AWS_DEFAULT_REGION
    assert calls['publish'][1]['iam_operations'] is policy._iam_operations
    # The secret must go straight to Jenkins: no local credentials file is created.
    assert not credentials_file.exists()
    new_key = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata'][0]
    assert published['access_key_id'] == new_key['AccessKeyId']


@mock_aws
def test_rotate_access_key_creates_directly_when_jenkins_has_only_one_key(tmp_path, monkeypatch):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    iam_client.create_user(UserName=TEST_USER_NAME)
    jenkins_key_id = iam_client.create_access_key(
        UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId']
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO, publish_to_jenkins=True)
    calls = {}

    class _FakeJenkins:
        @staticmethod
        def read_secret(credentials_id):
            return jenkins_key_id

    def fake_publish(credentials, client, **kwargs):
        calls['publish'] = credentials
        return {'username': TEST_USER_NAME, 'access_key_to_inactive': jenkins_key_id}

    monkeypatch.setattr(rotate_access_key_module, 'get_jenkins_client', lambda: _FakeJenkins())
    monkeypatch.setattr(rotate_access_key_module, 'rotate_and_publish_credentials', fake_publish)

    result = RotateAccessKey().run_policy_operations()

    assert result[0]['ResourceAction'] == 'True'
    published = calls['publish']
    assert published['access_key_id'] != jenkins_key_id
    assert published['secret_access_key']
    # No throwaway key was created; the Jenkins key stays Active until the publish deactivates it.
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    statuses = {key['AccessKeyId']: key['Status'] for key in keys}
    assert len(keys) == 2
    assert statuses[jenkins_key_id] == 'Active'
    assert statuses[published['access_key_id']] == 'Active'
    assert not credentials_file.exists()


@mock_aws
def test_rotate_access_key_skips_when_jenkins_preconditions_fail(tmp_path, monkeypatch):
    iam_client, inactive_key_id = _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO, publish_to_jenkins=True)

    def fail_preconditions(*args, **kwargs):
        raise JenkinsOperationsError('the key stored in Jenkins must be Active')

    monkeypatch.setattr(rotate_access_key_module, 'get_jenkins_client',
                        lambda: SimpleNamespace(read_secret=lambda credentials_id: 'AKIAOLDKEY'))
    monkeypatch.setattr(rotate_access_key_module, 'ensure_rotation_preconditions',
                        fail_preconditions)

    assert RotateAccessKey().run_policy_operations() == []
    keys = iam_client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in keys] == [inactive_key_id]
    assert not credentials_file.exists()


@mock_aws
def test_rotate_access_key_does_not_publish_in_dry_run(tmp_path, monkeypatch):
    _create_user_with_inactive_key()
    _set_environment_variables(tmp_path / 'creds.json', dry_run=DRY_RUN_YES,
                               publish_to_jenkins=True)

    def unexpected(*args, **kwargs):
        raise AssertionError('Jenkins must not be called in a dry run')

    monkeypatch.setattr(rotate_access_key_module, 'get_jenkins_client', unexpected)
    monkeypatch.setattr(rotate_access_key_module, 'ensure_rotation_preconditions', unexpected)
    monkeypatch.setattr(rotate_access_key_module, 'rotate_and_publish_credentials', unexpected)

    result = RotateAccessKey().run_policy_operations()

    assert result[0]['ResourceAction'] == 'False'


@mock_aws
def test_rotate_access_key_propagates_a_publish_failure(tmp_path, monkeypatch):
    _create_user_with_inactive_key()
    credentials_file = tmp_path / 'creds.json'
    _set_environment_variables(credentials_file, dry_run=DRY_RUN_NO, publish_to_jenkins=True)

    def fail_publish(*args, **kwargs):
        raise JenkinsOperationsError('Jenkins write failed')

    monkeypatch.setattr(rotate_access_key_module, 'get_jenkins_client',
                        lambda: SimpleNamespace(read_secret=lambda credentials_id: 'AKIAOLDKEY'))
    monkeypatch.setattr(rotate_access_key_module, 'ensure_rotation_preconditions',
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(rotate_access_key_module, 'rotate_and_publish_credentials', fail_publish)

    with pytest.raises(JenkinsOperationsError):
        RotateAccessKey().run_policy_operations()

    # Nothing was published, and the secret is never written to a local file on this path.
    assert not credentials_file.exists()
