"""
Integration test for JenkinsOperations against a real Jenkins instance.

The test is opt-in and self-skips: CI has no Jenkins, so `pytest -v tests/integration` stays green.
It creates a uniquely named secret-text credential, reads it back, updates the key, reads it
again, and deletes it.

The account must have Overall/Administer because reading a plaintext secret goes through the
Script Console (`POST /scriptText`). Run this only against a dedicated test Jenkins, never
production. Either an API token or a password can be used for basic auth:

    JENKINS_INTEGRATION=yes \
    JENKINS_URL=https://jenkins.example.com \
    JENKINS_USERNAME=test-user \
    JENKINS_API_TOKEN=... \
        python -m pytest tests/integration/cloud_governance/common/jenkins \
        -v -s

    JENKINS_INTEGRATION=yes \
    JENKINS_URL=https://jenkins.example.com \
    JENKINS_USERNAME=test-user \
    JENKINS_PASSWORD=... \
        python -m pytest tests/integration/cloud_governance/common/jenkins \
        -v -s

To read one existing credential only (no create/update/delete):

    JENKINS_INTEGRATION=yes \
    JENKINS_URL=https://jenkins.example.com \
    JENKINS_USERNAME=test-user \
    JENKINS_API_TOKEN=... \
    JENKINS_CREDENTIAL_ID=... \
        python -m pytest tests/integration/cloud_governance/common/jenkins \
        -v -k test_read_existing_secret

To write a temporary value into one existing credential and restore the original value:

    JENKINS_INTEGRATION=yes \
    JENKINS_URL=https://jenkins.example.com \
    JENKINS_USERNAME=test-user \
    JENKINS_API_TOKEN=... \
    JENKINS_CREDENTIAL_ID=... \
    JENKINS_WRITE_TEST=yes \
        python -m pytest tests/integration/cloud_governance/common/jenkins \
        -v -k test_write_existing_secret

Set JENKINS_WRITE_VALUE to write a specific value instead of a random marker; the original value
is restored unless JENKINS_WRITE_KEEP=yes is set, which leaves the written value in place.

The test never prints the secret value; set JENKINS_EXPECTED_SECRET to assert it exactly.
"""
import logging
import os
import uuid

import pytest

from cloud_governance.common.jenkins.jenkins_operations import JenkinsOperations

pytestmark = [
    pytest.mark.skipif(
        os.environ.get('JENKINS_INTEGRATION', '').lower() != 'yes',
        reason='set JENKINS_INTEGRATION=yes to run against a real Jenkins instance'),
    pytest.mark.skipif(
        not (os.environ.get('JENKINS_URL') and os.environ.get('JENKINS_USERNAME')
             and (os.environ.get('JENKINS_API_TOKEN') or os.environ.get('JENKINS_PASSWORD'))),
        reason='set JENKINS_URL, JENKINS_USERNAME and JENKINS_API_TOKEN or JENKINS_PASSWORD'),
]


def _client() -> JenkinsOperations:
    return JenkinsOperations(
        url=os.environ['JENKINS_URL'],
        username=os.environ['JENKINS_USERNAME'],
        api_token=os.environ.get('JENKINS_API_TOKEN', ''),
        password=os.environ.get('JENKINS_PASSWORD', ''),
        verify_ssl=os.environ.get('JENKINS_VERIFY_SSL', 'true').strip().lower()
        not in ('false', '0', 'no'),
        allow_script_console=True,
    )


def _assert_secret(actual: str, expected: str, message: str):
    # Explicit raise: a bare assert would make pytest print the secret in the failure output.
    if actual != expected:
        raise AssertionError(message)


def _assert_created(client: JenkinsOperations, credential_id: str, secret: str):
    if client.write_secret(credential_id, secret, description='integration test') != 'created':
        raise AssertionError('write_secret did not create the credential')
    if not client.credential_exists(credential_id):
        raise AssertionError('the created credential was not found')
    metadata = client.get_credential(credential_id)
    if metadata is None or metadata.get('id') != credential_id:
        raise AssertionError('get_credential did not return the created credential')
    if any('secret' in key.lower() for key in metadata):
        raise AssertionError('credential metadata unexpectedly contains a secret field')
    if credential_id not in {item.get('id') for item in client.list_credentials()}:
        raise AssertionError('the created credential is missing from list_credentials')


def _assert_updated(client: JenkinsOperations, credential_id: str, secret: str):
    if client.write_secret(credential_id, secret) != 'updated':
        raise AssertionError('write_secret did not update the existing credential')
    _assert_secret(client.read_secret(credential_id), secret,
                   'read_secret did not return the value written by update')


def _assert_deleted(client: JenkinsOperations, credential_id: str):
    if client.delete_secret(credential_id) is not True:
        raise AssertionError('delete_secret did not delete the credential')
    if client.credential_exists(credential_id):
        raise AssertionError('the credential still exists after delete')
    if client.delete_secret(credential_id) is not False:
        raise AssertionError('a second delete of a missing credential did not return False')


READ_CREDENTIAL_ID = os.environ.get('JENKINS_CREDENTIAL_ID', '').strip()


@pytest.mark.skipif(not READ_CREDENTIAL_ID,
                    reason='set JENKINS_CREDENTIAL_ID to read one existing credential')
def test_read_existing_secret(caplog):
    """
    Reads one existing credential and asserts the call succeeds. Nothing is created, updated or
    deleted, so this is safe to point at a real credential.

    Set JENKINS_EXPECTED_SECRET to also assert the exact value. The value is never printed.
    """
    client = _client()

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        secret = client.read_secret(READ_CREDENTIAL_ID)

    if not secret:
        raise AssertionError('read_secret returned an empty value')
    expected = os.environ.get('JENKINS_EXPECTED_SECRET')
    if expected is not None and secret != expected:
        raise AssertionError('read_secret did not return the expected value')
    if READ_CREDENTIAL_ID in caplog.text:
        raise AssertionError('the credential id was written to the log')
    if expected and expected in caplog.text:
        raise AssertionError('the secret was written to the log')


WRITE_TEST_ENABLED = os.environ.get('JENKINS_WRITE_TEST', '').strip().lower() == 'yes'


@pytest.mark.skipif(not READ_CREDENTIAL_ID,
                    reason='set JENKINS_CREDENTIAL_ID to target one existing credential')
@pytest.mark.skipif(not WRITE_TEST_ENABLED,
                    reason='set JENKINS_WRITE_TEST=yes to write to and restore an existing credential')
def test_write_existing_secret(caplog):
    """
    Writes a temporary value into one existing credential, verifies the new value can be read
    back, and restores the original value.

    This mutates a real credential, so it requires JENKINS_WRITE_TEST=yes in addition to
    JENKINS_CREDENTIAL_ID. The original value is read first and restored in a finally block, and
    the restore is verified by reading the credential again. Set JENKINS_WRITE_KEEP=yes to leave
    the written value in place instead of restoring the original.
    """
    client = _client()
    original = client.read_secret(READ_CREDENTIAL_ID)
    # JENKINS_WRITE_VALUE lets the caller write a specific value; the default is a random marker.
    temporary = os.environ.get('JENKINS_WRITE_VALUE') or f'integration-write-{uuid.uuid4().hex}'
    keep_value = os.environ.get('JENKINS_WRITE_KEEP', '').strip().lower() == 'yes'

    try:
        with caplog.at_level(logging.INFO, logger='cloud_governance'):
            if client.write_secret(READ_CREDENTIAL_ID, temporary) != 'updated':
                raise AssertionError('write_secret did not update the existing credential')
            _assert_secret(client.read_secret(READ_CREDENTIAL_ID), temporary,
                           'read_secret did not return the value written by write_secret')
    finally:
        if not keep_value:
            client.update_secret(READ_CREDENTIAL_ID, original)
            _assert_secret(client.read_secret(READ_CREDENTIAL_ID), original,
                           'the original credential value was not restored')

    for value in (original, temporary, READ_CREDENTIAL_ID):
        if value and value in caplog.text:
            raise AssertionError('a sensitive value was written to the log')


def test_read_write_secret(caplog):
    client = _client()
    credential_id = f'integration-jenkins-{uuid.uuid4().hex[:12]}'
    first_secret = uuid.uuid4().hex
    second_secret = uuid.uuid4().hex
    sensitive_values = (
        first_secret, second_secret, credential_id,
        os.environ['JENKINS_USERNAME'],
        os.environ.get('JENKINS_API_TOKEN', ''),
        os.environ.get('JENKINS_PASSWORD', ''),
    )

    try:
        with caplog.at_level(logging.INFO, logger='cloud_governance'):
            _assert_created(client, credential_id, first_secret)
            _assert_secret(client.read_secret(credential_id), first_secret,
                           'read_secret did not return the value written by create')
            _assert_updated(client, credential_id, second_secret)
            _assert_deleted(client, credential_id)
    finally:
        try:
            client.delete_secret(credential_id)
        except Exception:
            pass

    for value in sensitive_values:
        if value and value in caplog.text:
            raise AssertionError('a sensitive value was written to the log')
