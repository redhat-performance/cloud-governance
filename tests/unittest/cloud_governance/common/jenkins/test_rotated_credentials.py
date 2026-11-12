"""
Unit tests for cloud_governance.common.jenkins.rotated_credentials.
"""
import json
import logging
import os
import stat
from types import SimpleNamespace

import boto3
import pytest
from moto import mock_aws

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.jenkins.rotated_credentials import (
    DEFAULT_ACCESS_KEY_CREDENTIAL_ID,
    DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID,
    deactivate_previous_access_key,
    ensure_jenkins_key_is_active,
    ensure_rotation_preconditions,
    get_default_credential_ids,
    has_free_key_slot,
    load_rotated_credentials,
    prepare_inactive_key,
    publish_rotated_credentials,
    rotate_and_publish_credentials,
    rotate_and_publish_to_jenkins,
    update_rotated_credentials,
)
from cloud_governance.main.environment_variables import environment_variables
from tests.unittest.configs import AWS_DEFAULT_REGION, TEST_USER_NAME

CREDENTIALS = {
    'username': 'test-user',
    'access_key_id': 'AKIANEWEXAMPLE',
    'secret_access_key': 'new-secret',
    'created_at': '2026-11-04T00:00:00+00:00',
}


@pytest.fixture(autouse=True)
def _isolate_credential_id_environment(monkeypatch):
    """Keeps the tests independent of JENKINS_* variables exported in the caller's shell."""
    env = environment_variables.environment_variables_dict
    monkeypatch.setitem(env, 'JENKINS_ACCESS_KEY_CREDENTIAL_ID', '')
    monkeypatch.setitem(env, 'JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID', '')


class _FakeClient:
    """Records calls and returns a canned current access key id."""

    def __init__(self, current: str = 'OLDKEY', fail_read: bool = False,
                 fail_write_at: int = None, read_sequence: list = None):
        self.calls = []
        self.current = current
        self.fail_read = fail_read
        self.fail_write_at = fail_write_at
        self.read_sequence = read_sequence
        self.write_count = 0

    def read_secret(self, credentials_id: str):
        self.calls.append(('read', credentials_id))
        if self.fail_read:
            raise JenkinsOperationsError('read failed')
        if self.read_sequence is not None:
            return self.read_sequence.pop(0)
        return self.current

    def write_secret(self, credentials_id: str, secret: str, description: str = ''):
        self.calls.append(('write', credentials_id, secret))
        self.write_count += 1
        if self.fail_write_at == self.write_count:
            raise JenkinsOperationsError('write failed')
        return 'updated'


def _write_credentials_file(tmp_path, payload) -> str:
    credentials_file = tmp_path / 'iam_credentials.json'
    credentials_file.write_text(json.dumps(payload))
    return str(credentials_file)


# ---------------------------------------------------------------------------
# load_rotated_credentials
# ---------------------------------------------------------------------------

def test_load_returns_the_validated_payload(tmp_path):
    payload = load_rotated_credentials(_write_credentials_file(tmp_path, CREDENTIALS))
    assert payload == CREDENTIALS


def test_load_rejects_a_missing_file(tmp_path):
    missing = str(tmp_path / 'does-not-exist.json')
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(missing)
    assert 'was not found' in str(error.value)
    assert missing not in str(error.value)


def test_load_rejects_invalid_json(tmp_path):
    credentials_file = tmp_path / 'bad.json'
    credentials_file.write_text('{not json')
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(str(credentials_file))
    assert 'could not be read' in str(error.value)


def test_load_rejects_a_non_object_payload(tmp_path):
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(_write_credentials_file(tmp_path, ['not', 'an', 'object']))
    assert 'must be a JSON object' in str(error.value)


@pytest.mark.parametrize('field', ['username', 'access_key_id', 'secret_access_key'])
def test_load_rejects_a_missing_field(tmp_path, field):
    payload = dict(CREDENTIALS)
    payload.pop(field)
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(_write_credentials_file(tmp_path, payload))
    assert f'missing a valid {field}' in str(error.value)


@pytest.mark.parametrize('field', ['username', 'access_key_id', 'secret_access_key'])
def test_load_rejects_an_empty_field_without_echoing_it(tmp_path, field):
    payload = dict(CREDENTIALS)
    payload[field] = '  '
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(_write_credentials_file(tmp_path, payload))
    assert f'missing a valid {field}' in str(error.value)


@pytest.mark.parametrize('field', ['username', 'access_key_id', 'secret_access_key'])
def test_load_rejects_a_non_string_field(tmp_path, field):
    payload = dict(CREDENTIALS)
    payload[field] = 123
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials(_write_credentials_file(tmp_path, payload))
    assert f'missing a valid {field}' in str(error.value)


def test_load_rejects_an_empty_path():
    with pytest.raises(JenkinsOperationsError) as error:
        load_rotated_credentials('')
    assert 'path must be a non-empty string' in str(error.value)


# ---------------------------------------------------------------------------
# publish_rotated_credentials
# ---------------------------------------------------------------------------

def test_publish_reads_the_current_key_before_writing():
    client = _FakeClient(current='OLDKEY')

    result = publish_rotated_credentials(client, CREDENTIALS)

    assert client.calls == [
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('write', DEFAULT_ACCESS_KEY_CREDENTIAL_ID, 'AKIANEWEXAMPLE'),
        ('write', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID, 'new-secret'),
    ]
    assert result == {'username': 'test-user', 'access_key_to_inactive': 'OLDKEY'}


def test_publish_honors_custom_credential_ids():
    client = _FakeClient(current='OLDKEY')

    result = publish_rotated_credentials(
        client, CREDENTIALS,
        access_key_credential_id='custom-access-key-id',
        secret_access_key_credential_id='custom-secret-access-key')

    assert client.calls == [
        ('read', 'custom-access-key-id'),
        ('write', 'custom-access-key-id', 'AKIANEWEXAMPLE'),
        ('write', 'custom-secret-access-key', 'new-secret'),
    ]
    assert result['access_key_to_inactive'] == 'OLDKEY'


def test_get_default_credential_ids_falls_back_to_the_ebattat_ids():
    assert get_default_credential_ids() == (DEFAULT_ACCESS_KEY_CREDENTIAL_ID,
                                            DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID)


def test_publish_uses_credential_ids_from_the_environment(monkeypatch):
    env = environment_variables.environment_variables_dict
    monkeypatch.setitem(env, 'JENKINS_ACCESS_KEY_CREDENTIAL_ID', 'env-access-key-id')
    monkeypatch.setitem(env, 'JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID', 'env-secret-key-id')
    client = _FakeClient(current='OLDKEY')

    result = publish_rotated_credentials(client, CREDENTIALS)

    assert client.calls == [
        ('read', 'env-access-key-id'),
        ('write', 'env-access-key-id', 'AKIANEWEXAMPLE'),
        ('write', 'env-secret-key-id', 'new-secret'),
    ]
    assert result['access_key_to_inactive'] == 'OLDKEY'


def test_publish_trims_environment_ids_and_falls_back_when_blank(monkeypatch):
    env = environment_variables.environment_variables_dict
    monkeypatch.setitem(env, 'JENKINS_ACCESS_KEY_CREDENTIAL_ID', '  env-access-key-id  ')
    monkeypatch.setitem(env, 'JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID', '   ')
    client = _FakeClient()

    publish_rotated_credentials(client, CREDENTIALS)

    assert client.calls == [
        ('read', 'env-access-key-id'),
        ('write', 'env-access-key-id', 'AKIANEWEXAMPLE'),
        ('write', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID, 'new-secret'),
    ]


def test_publish_prefers_explicit_ids_over_the_environment(monkeypatch):
    env = environment_variables.environment_variables_dict
    monkeypatch.setitem(env, 'JENKINS_ACCESS_KEY_CREDENTIAL_ID', 'env-access-key-id')
    monkeypatch.setitem(env, 'JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID', 'env-secret-key-id')
    client = _FakeClient()

    publish_rotated_credentials(client, CREDENTIALS,
                                access_key_credential_id='explicit-access-key-id',
                                secret_access_key_credential_id='explicit-secret-key-id')

    assert client.calls == [
        ('read', 'explicit-access-key-id'),
        ('write', 'explicit-access-key-id', 'AKIANEWEXAMPLE'),
        ('write', 'explicit-secret-key-id', 'new-secret'),
    ]


def test_publish_validates_before_reading():
    client = _FakeClient()
    payload = dict(CREDENTIALS)
    payload['access_key_id'] = ''

    with pytest.raises(JenkinsOperationsError):
        publish_rotated_credentials(client, payload)

    assert client.calls == []


def test_publish_does_not_write_when_the_read_fails():
    client = _FakeClient(fail_read=True)

    with pytest.raises(JenkinsOperationsError):
        publish_rotated_credentials(client, CREDENTIALS)

    assert client.calls == [('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID)]


def test_publish_propagates_a_write_failure():
    client = _FakeClient(fail_write_at=2)

    with pytest.raises(JenkinsOperationsError):
        publish_rotated_credentials(client, CREDENTIALS)

    assert client.calls == [
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('write', DEFAULT_ACCESS_KEY_CREDENTIAL_ID, 'AKIANEWEXAMPLE'),
        ('write', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID, 'new-secret'),
    ]


def test_publish_logs_events_without_sensitive_values(caplog):
    client = _FakeClient(current='OLDKEY')

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        publish_rotated_credentials(client, CREDENTIALS)

    assert 'Updated the Jenkins access key credential' in caplog.text
    assert 'Updated the Jenkins secret access key credential' in caplog.text
    for value in ('OLDKEY', 'AKIANEWEXAMPLE', 'new-secret', 'test-user',
                  DEFAULT_ACCESS_KEY_CREDENTIAL_ID, DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID):
        assert value not in caplog.text


# ---------------------------------------------------------------------------
# deactivate_previous_access_key / rotate_and_publish_to_jenkins
# ---------------------------------------------------------------------------

PUBLISHED = {'username': 'test-user', 'access_key_to_inactive': 'OLDKEY'}


class _FakeIAMOperations:
    """Records the deactivation calls instead of talking to AWS."""

    def __init__(self, error: Exception = None):
        self.deactivate_calls = []
        self.stale_calls = []
        self.error = error

    def deactivate_access_key_with_credentials(self, **kwargs):
        self.deactivate_calls.append(kwargs)
        if self.error:
            raise self.error

    def deactivate_stale_active_keys(self, **kwargs):
        self.stale_calls.append(kwargs)
        if self.error:
            raise self.error


def _new_credentials_client() -> _FakeClient:
    """Returns the new access key id and secret, in that order."""
    return _FakeClient(read_sequence=['AKIANEWEXAMPLE', 'new-secret'])


def test_deactivate_reads_new_credentials_from_jenkins_and_authenticates_with_them():
    client = _new_credentials_client()
    iam = _FakeIAMOperations()

    deactivate_previous_access_key(client, PUBLISHED, region_name='us-east-1',
                                   iam_operations=iam)

    assert client.calls == [('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
                            ('read', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID)]
    assert iam.deactivate_calls == [{
        'username': 'test-user',
        'access_key_id': 'OLDKEY',
        'aws_access_key_id': 'AKIANEWEXAMPLE',
        'aws_secret_access_key': 'new-secret',
        'region_name': 'us-east-1',
    }]
    assert iam.stale_calls == [{
        'username': 'test-user',
        'keep_access_key_id': 'AKIANEWEXAMPLE',
        'aws_access_key_id': 'AKIANEWEXAMPLE',
        'aws_secret_access_key': 'new-secret',
        'region_name': 'us-east-1',
    }]


def test_deactivate_can_skip_stale_key_cleanup():
    iam = _FakeIAMOperations()

    deactivate_previous_access_key(_new_credentials_client(), PUBLISHED,
                                   iam_operations=iam, deactivate_stale_keys=False)

    assert len(iam.deactivate_calls) == 1
    assert iam.stale_calls == []


def test_deactivate_honors_custom_credential_ids():
    client = _new_credentials_client()
    iam = _FakeIAMOperations()

    deactivate_previous_access_key(
        client, PUBLISHED,
        access_key_credential_id='custom-access-key-id',
        secret_access_key_credential_id='custom-secret-access-key',
        iam_operations=iam)

    assert client.calls == [('read', 'custom-access-key-id'),
                            ('read', 'custom-secret-access-key')]


def test_deactivate_defaults_the_region_to_aws_default_region(monkeypatch):
    monkeypatch.setitem(environment_variables.environment_variables_dict,
                        'AWS_DEFAULT_REGION', 'eu-west-1')
    iam = _FakeIAMOperations()

    deactivate_previous_access_key(_new_credentials_client(), PUBLISHED,
                                   iam_operations=iam)

    assert iam.deactivate_calls[0]['region_name'] == 'eu-west-1'
    assert iam.stale_calls[0]['region_name'] == 'eu-west-1'


@pytest.mark.parametrize('result', [
    'not-a-dict',
    {'username': 'test-user'},
    {'access_key_to_inactive': 'OLDKEY'},
    {'username': '  ', 'access_key_to_inactive': 'OLDKEY'},
    {'username': 'test-user', 'access_key_to_inactive': ''},
])
def test_deactivate_rejects_an_invalid_publish_result(result):
    client = _FakeClient()

    with pytest.raises(JenkinsOperationsError):
        deactivate_previous_access_key(client, result, iam_operations=_FakeIAMOperations())

    assert client.calls == []


def test_deactivate_propagates_an_iam_failure():
    with pytest.raises(RuntimeError):
        deactivate_previous_access_key(
            _new_credentials_client(), PUBLISHED,
            iam_operations=_FakeIAMOperations(error=RuntimeError('failed')))


def test_deactivate_logs_without_sensitive_values(caplog):
    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        deactivate_previous_access_key(_new_credentials_client(), PUBLISHED,
                                       iam_operations=_FakeIAMOperations())

    assert 'Deactivated the previous access key' in caplog.text
    for value in ('OLDKEY', 'AKIANEWEXAMPLE', 'new-secret', 'test-user'):
        assert value not in caplog.text


def test_update_merges_fields_into_the_file_and_keeps_it_private(tmp_path):
    credentials_file = _write_credentials_file(tmp_path, CREDENTIALS)

    updated = update_rotated_credentials(credentials_file,
                                         {'access_key_to_inactive': 'OLDKEY'})

    assert updated['access_key_to_inactive'] == 'OLDKEY'
    assert updated['access_key_id'] == CREDENTIALS['access_key_id']
    with open(credentials_file) as file:
        assert json.load(file) == updated
    assert stat.S_IMODE(os.stat(credentials_file).st_mode) == 0o600


def test_update_rejects_non_dict_updates(tmp_path):
    with pytest.raises(JenkinsOperationsError):
        update_rotated_credentials(_write_credentials_file(tmp_path, CREDENTIALS), 'not-a-dict')


def test_update_rejects_a_missing_file(tmp_path):
    with pytest.raises(JenkinsOperationsError):
        update_rotated_credentials(str(tmp_path / 'missing.json'),
                                   {'access_key_to_inactive': 'OLDKEY'})


def test_rotate_and_publish_runs_publish_then_deactivate(tmp_path):
    # Read order: publish reads the old id; deactivate reads the new id and the new secret.
    client = _FakeClient(read_sequence=['OLDKEY', 'AKIANEWEXAMPLE', 'new-secret'])
    iam = _FakeIAMOperations()
    credentials_file = _write_credentials_file(tmp_path, CREDENTIALS)

    result = rotate_and_publish_to_jenkins(credentials_file, client, region_name='us-east-1',
                                           iam_operations=iam)

    assert result == {'username': 'test-user', 'access_key_to_inactive': 'OLDKEY'}
    with open(credentials_file) as file:
        stored = json.load(file)
    assert stored['access_key_to_inactive'] == 'OLDKEY'
    assert stored['access_key_id'] == CREDENTIALS['access_key_id']
    assert client.calls == [
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('write', DEFAULT_ACCESS_KEY_CREDENTIAL_ID, 'AKIANEWEXAMPLE'),
        ('write', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID, 'new-secret'),
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('read', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID),
    ]
    assert iam.deactivate_calls == [{
        'username': 'test-user',
        'access_key_id': 'OLDKEY',
        'aws_access_key_id': 'AKIANEWEXAMPLE',
        'aws_secret_access_key': 'new-secret',
        'region_name': 'us-east-1',
    }]
    assert iam.stale_calls == [{
        'username': 'test-user',
        'keep_access_key_id': 'AKIANEWEXAMPLE',
        'aws_access_key_id': 'AKIANEWEXAMPLE',
        'aws_secret_access_key': 'new-secret',
        'region_name': 'us-east-1',
    }]


def test_rotate_and_publish_credentials_works_in_memory_without_a_file(tmp_path):
    # The same sequence as the file-based path, but no path is read or written.
    client = _FakeClient(read_sequence=['OLDKEY', 'AKIANEWEXAMPLE', 'new-secret'])
    iam = _FakeIAMOperations()

    result = rotate_and_publish_credentials(CREDENTIALS, client, region_name='us-east-1',
                                            iam_operations=iam)

    assert result == {'username': 'test-user', 'access_key_to_inactive': 'OLDKEY'}
    assert client.calls == [
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('write', DEFAULT_ACCESS_KEY_CREDENTIAL_ID, 'AKIANEWEXAMPLE'),
        ('write', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID, 'new-secret'),
        ('read', DEFAULT_ACCESS_KEY_CREDENTIAL_ID),
        ('read', DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID),
    ]
    assert iam.deactivate_calls == [{
        'username': 'test-user',
        'access_key_id': 'OLDKEY',
        'aws_access_key_id': 'AKIANEWEXAMPLE',
        'aws_secret_access_key': 'new-secret',
        'region_name': 'us-east-1',
    }]
    assert os.listdir(tmp_path) == []


def test_rotate_and_publish_credentials_rejects_an_invalid_payload_before_reading():
    client = _FakeClient()

    with pytest.raises(JenkinsOperationsError):
        rotate_and_publish_credentials({'username': 'test-user'}, client)

    assert client.calls == []


# ---------------------------------------------------------------------------
# Rotation preconditions
# ---------------------------------------------------------------------------

def _iam_client():
    return boto3.client('iam', region_name=AWS_DEFAULT_REGION)


def _iam_operations(client):
    return SimpleNamespace(get_iam_client=client)


def _create_user_with_keys(client, active: int = 0, inactive: int = 0) -> dict:
    """Creates the test user and returns the created active and inactive key ids."""
    client.create_user(UserName=TEST_USER_NAME)
    keys = {'active': [], 'inactive': []}
    for _ in range(active):
        keys['active'].append(
            client.create_access_key(UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId'])
    for _ in range(inactive):
        key_id = client.create_access_key(
            UserName=TEST_USER_NAME)['AccessKey']['AccessKeyId']
        client.update_access_key(UserName=TEST_USER_NAME, AccessKeyId=key_id, Status='Inactive')
        keys['inactive'].append(key_id)
    return keys


def _key_status(client, key_id: str) -> str:
    metadata = client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    return {key['AccessKeyId']: key['Status'] for key in metadata}[key_id]


@mock_aws
def test_ensure_jenkins_key_is_active_reactivates_an_inactive_jenkins_key(caplog):
    client = _iam_client()
    keys = _create_user_with_keys(client, inactive=1)

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        ensure_jenkins_key_is_active(_iam_operations(client), TEST_USER_NAME,
                                     keys['inactive'][0])

    assert _key_status(client, keys['inactive'][0]) == 'Active'
    assert keys['inactive'][0] not in caplog.text


@mock_aws
def test_ensure_jenkins_key_is_active_rejects_a_missing_key():
    client = _iam_client()
    _create_user_with_keys(client, active=1)

    with pytest.raises(JenkinsOperationsError) as error:
        ensure_jenkins_key_is_active(_iam_operations(client), TEST_USER_NAME,
                                     'AKIAMISSINGEXAMPLE')

    assert 'does not exist' in str(error.value)
    assert 'AKIAMISSINGEXAMPLE' not in str(error.value)


@mock_aws
def test_prepare_inactive_key_keeps_an_existing_inactive_key():
    client = _iam_client()
    keys = _create_user_with_keys(client, active=1, inactive=1)

    assert prepare_inactive_key(_iam_operations(client), TEST_USER_NAME,
                                keys['active'][0]) is True
    assert _key_status(client, keys['active'][0]) == 'Active'
    assert _key_status(client, keys['inactive'][0]) == 'Inactive'


@mock_aws
def test_prepare_inactive_key_deactivates_a_stale_active_key(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIACALLEREXAMPLE')
    client = _iam_client()
    keys = _create_user_with_keys(client, active=2)
    jenkins_key, stale_key = keys['active']

    assert prepare_inactive_key(_iam_operations(client), TEST_USER_NAME, jenkins_key) is True
    assert _key_status(client, jenkins_key) == 'Active'
    assert _key_status(client, stale_key) == 'Inactive'


@mock_aws
def test_prepare_inactive_key_creates_no_key_when_one_slot_is_free(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIACALLEREXAMPLE')
    client = _iam_client()
    keys = _create_user_with_keys(client, active=1)
    jenkins_key = keys['active'][0]

    # No inactive key exists and none is created: the rotation creates directly in the free slot.
    assert prepare_inactive_key(_iam_operations(client), TEST_USER_NAME, jenkins_key) is False
    metadata = client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in metadata] == [jenkins_key]
    assert _key_status(client, jenkins_key) == 'Active'


@mock_aws
def test_has_free_key_slot_is_true_with_a_single_key():
    client = _iam_client()
    _create_user_with_keys(client, active=1)

    assert has_free_key_slot(_iam_operations(client), TEST_USER_NAME) is True


@mock_aws
def test_has_free_key_slot_is_false_with_two_keys():
    client = _iam_client()
    _create_user_with_keys(client, active=2)

    assert has_free_key_slot(_iam_operations(client), TEST_USER_NAME) is False


@mock_aws
def test_prepare_inactive_key_does_not_guess_when_the_caller_key_is_unknown(monkeypatch):
    client = _iam_client()
    keys = _create_user_with_keys(client, active=2)
    jenkins_key, other_key = keys['active']
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', '')

    assert prepare_inactive_key(_iam_operations(client), TEST_USER_NAME, jenkins_key) is False
    assert _key_status(client, jenkins_key) == 'Active'
    assert _key_status(client, other_key) == 'Active'


@mock_aws
def test_prepare_inactive_key_returns_false_when_both_keys_are_in_use(monkeypatch):
    client = _iam_client()
    keys = _create_user_with_keys(client, active=2)
    jenkins_key, caller_key = keys['active']
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', caller_key)

    assert prepare_inactive_key(_iam_operations(client), TEST_USER_NAME, jenkins_key) is False
    assert _key_status(client, jenkins_key) == 'Active'
    assert _key_status(client, caller_key) == 'Active'


@mock_aws
def test_ensure_rotation_preconditions_allows_a_free_slot_without_creating_a_key():
    client = _iam_client()
    keys = _create_user_with_keys(client, active=1)
    jenkins_key = keys['active'][0]

    ensure_rotation_preconditions(_iam_operations(client), TEST_USER_NAME, jenkins_key)

    metadata = client.list_access_keys(UserName=TEST_USER_NAME)['AccessKeyMetadata']
    assert [key['AccessKeyId'] for key in metadata] == [jenkins_key]


@mock_aws
def test_ensure_rotation_preconditions_raises_when_no_key_can_be_prepared(monkeypatch):
    client = _iam_client()
    keys = _create_user_with_keys(client, active=2)
    jenkins_key, caller_key = keys['active']
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', caller_key)

    with pytest.raises(JenkinsOperationsError) as error:
        ensure_rotation_preconditions(_iam_operations(client), TEST_USER_NAME, jenkins_key)

    assert 'no free slot' in str(error.value)
    assert jenkins_key not in str(error.value)
    assert caller_key not in str(error.value)
