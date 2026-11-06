"""
End-to-end test: rotate_access_key -> IAM_CREDENTIALS_FILE -> Jenkins credentials.

Nothing runs unless JENKINS_ROTATION_E2E=yes, so CI and normal pytest runs are unaffected.

The real-user e2e needs only the variables below (for example in ~/.cg-e2e.env); nothing else
is required. AWS credentials are used by the IAM setup and by RotateAccessKey through boto3's
default chain. Never put the values in the test or in its output; export them in the shell.

    export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=us-east-1
    export JENKINS_URL=... JENKINS_USERNAME=... JENKINS_API_TOKEN=... JENKINS_VERIFY_SSL=false
    export JENKINS_ACCESS_KEY_CREDENTIAL_ID=EBATTAT_AWS_ACCESS_KEY_ID
    export JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID=EBATTAT_AWS_SECRET_ACCESS_KEY
    export username=<iam-user>
    export JENKINS_ROTATION_E2E=yes
    export IAM_ROTATE_TEST_CONFIRM=yes
    export JENKINS_REAL_CREDENTIALS_CONFIRM=yes

    python -m pytest tests/integration/cloud_governance/common/jenkins/test_rotate_and_publish.py -v

1. test_rotate_real_user_and_publish rewrites the Jenkins credentials named by
   JENKINS_ACCESS_KEY_CREDENTIAL_ID and JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID (default
   EBATTAT_AWS_ACCESS_KEY_ID and EBATTAT_AWS_SECRET_ACCESS_KEY) with a newly rotated key of a
   real IAM user. The key stored in Jenkins must be Active, and the flow only ever deactivates
   it: the policy consumes a different inactive key, deletes it, and creates a new one; the test
   publishes the new values to Jenkins and then deactivates the previous Jenkins key (returned
   as access_key_to_inactive) by authenticating with the new credentials just read back from
   Jenkins. Any other Active key of the user is deactivated too, except the caller's own key.
   An Inactive Jenkins key is reactivated first, and when the account has no inactive key the
   test prepares one (deactivating a stale Active key or creating and deactivating a new one
   when there is a free slot) without touching the caller's key. The caller may be the key
   stored in Jenkins (self-rotation): that key is deactivated at the end, so the caller must
   switch to the newly published key afterwards, and the post-run checks use it. If the caller is
   a different key of the target user and both key slots are Active, no separate key is available
   for the rotation to consume and the test skips before rotating. It fails before rotating if
   the Jenkins key does not belong to the requested user or no longer exists.

2. test_rotation_to_jenkins_with_temp_user is optional and disabled by default: it also needs
   JENKINS_TEMP_USER_E2E=yes. It is self-contained: it creates a temporary IAM user with an
   inactive key, rotates it, and publishes the new credentials to two throwaway Jenkins
   credentials that are deleted afterwards. The AWS caller needs iam:CreateUser, CreateAccessKey,
   UpdateAccessKey, ListAccessKeys, DeleteAccessKey and DeleteUser.

    JENKINS_TEMP_USER_E2E=yes \
        python -m pytest tests/integration/cloud_governance/common/jenkins/test_rotate_and_publish.py \
        -k test_rotation_to_jenkins_with_temp_user -v
"""
import logging
import os
import uuid
from types import SimpleNamespace

import boto3
import pytest
from botocore.exceptions import ClientError

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.jenkins.jenkins_operations import JenkinsOperations
from cloud_governance.common.jenkins.rotated_credentials import (
    ensure_rotation_preconditions,
    get_default_credential_ids,
    load_rotated_credentials,
    publish_rotated_credentials,
    rotate_and_publish_to_jenkins,
)
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.rotate_access_key import RotateAccessKey, _ROTATED_USERS

AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
REAL_USER = os.environ.get('username', '').strip()
REAL_USER_CONFIRMED = os.environ.get('IAM_ROTATE_TEST_CONFIRM', '').lower() == 'yes'
REAL_CREDENTIALS_CONFIRMED = \
    os.environ.get('JENKINS_REAL_CREDENTIALS_CONFIRM', '').lower() == 'yes'
ROTATION_E2E_ENABLED = os.environ.get('JENKINS_ROTATION_E2E', '').lower() == 'yes'
TEMP_USER_E2E_ENABLED = os.environ.get('JENKINS_TEMP_USER_E2E', '').lower() == 'yes'


def _has_aws_credentials() -> bool:
    """Checks boto3's credential chain without making a network call."""
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        return True
    try:
        return boto3.session.Session().get_credentials() is not None
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(
        not ROTATION_E2E_ENABLED,
        reason='set JENKINS_ROTATION_E2E=yes to run the rotation-to-Jenkins flow'),
    # Short-circuits when the flow is disabled, so normal runs never probe the credential chain.
    pytest.mark.skipif(
        ROTATION_E2E_ENABLED and not _has_aws_credentials(),
        reason='set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or configure an AWS profile'),
    pytest.mark.skipif(
        not (os.environ.get('JENKINS_URL') and os.environ.get('JENKINS_USERNAME')
             and (os.environ.get('JENKINS_API_TOKEN') or os.environ.get('JENKINS_PASSWORD'))),
        reason='set JENKINS_URL, JENKINS_USERNAME and JENKINS_API_TOKEN or JENKINS_PASSWORD'),
]


def _iam_client_with_credentials(access_key_id: str, secret_access_key: str):
    """Builds an IAM client with explicit keys so a caller's session token cannot leak in."""
    return boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=AWS_DEFAULT_REGION,
    ).client('iam')


def _jenkins_client() -> JenkinsOperations:
    return JenkinsOperations(
        url=os.environ['JENKINS_URL'],
        username=os.environ['JENKINS_USERNAME'],
        api_token=os.environ.get('JENKINS_API_TOKEN', ''),
        password=os.environ.get('JENKINS_PASSWORD', ''),
        verify_ssl=os.environ.get('JENKINS_VERIFY_SSL', 'true').strip().lower()
        not in ('false', '0', 'no'),
        allow_script_console=True,
    )


def _assert_equal(actual, expected, message: str):
    # Explicit raise: a bare assert would make pytest print the access key in the failure output.
    if actual != expected:
        raise AssertionError(message)


def _run_aws_call(call, **kwargs):
    """
    Runs one IAM call and reports only the error code. A ClientError message contains the caller
    ARN (and therefore the account id), so it must never reach the pytest output.
    """
    try:
        return call(**kwargs)
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        raise AssertionError(f'AWS rejected an IAM call needed by this test ({code})') from None


def _set_policy_environment(username: str, credentials_file):
    environment_variables.environment_variables_dict['policy'] = 'rotate_access_key'
    environment_variables.environment_variables_dict['username'] = username
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = str(credentials_file)
    # The test publishes and deactivates itself; the policy must not run that step twice.
    environment_variables.environment_variables_dict['IAM_PUBLISH_TO_JENKINS'] = False


def _reset_policy_environment():
    _ROTATED_USERS.clear()
    environment_variables.environment_variables_dict['username'] = ''
    environment_variables.environment_variables_dict['IAM_CREDENTIALS_FILE'] = ''
    environment_variables.environment_variables_dict['IAM_PUBLISH_TO_JENKINS'] = False


def _run_rotation_policy() -> list:
    """Runs the policy and reports only an AWS error code, never the caller ARN."""
    try:
        return RotateAccessKey().run_policy_operations()
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        raise AssertionError(f'the rotation policy failed with an AWS error ({code})') from None


def _create_inactive_key(iam_client, username: str) -> str:
    key_id = _run_aws_call(iam_client.create_access_key,
                           UserName=username)['AccessKey']['AccessKeyId']
    _run_aws_call(iam_client.update_access_key,
                  UserName=username, AccessKeyId=key_id, Status='Inactive')
    return key_id


def _delete_iam_user(iam_client, username: str):
    try:
        for key in iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']:
            iam_client.delete_access_key(UserName=username, AccessKeyId=key['AccessKeyId'])
        iam_client.delete_user(UserName=username)
    except Exception:
        pass


def _assert_jenkins_key_belongs_to_user(iam_client, username: str, access_key_id: str):
    """
    Fails before rotating or publishing if the Jenkins credential and username do not describe
    the same IAM user, or if the credentials running this test are rejected. Never echoes ids.
    """
    owner = _access_key_owner(iam_client, username, access_key_id)
    if owner == 'error:AccessDenied':
        raise AssertionError(
            'the AWS credentials running this test are valid but lack IAM permissions '
            '(AccessDenied); grant iam:GetUser, iam:ListAccessKeys, iam:CreateAccessKey, '
            'iam:UpdateAccessKey and iam:DeleteAccessKey on the target user')
    if owner.startswith('error:'):
        code = owner.split(':', 1)[1]
        if os.environ.get('AWS_ACCESS_KEY_ID') == access_key_id:
            hint = ('the rejected key is the one stored in Jenkins; check that its secret is '
                    'correct and that the key is Active')
        else:
            hint = ('the rejected key is not the one stored in Jenkins; it is probably the '
                    'inactive key, use the Active key or credentials of another identity')
        raise AssertionError(
            f'the AWS credentials running this test were rejected by IAM ({code}); {hint}')
    if owner == 'missing':
        raise AssertionError(
            'the access key stored in Jenkins no longer exists in IAM (or belongs to another '
            'user); update the Jenkins access key and secret credentials with a live Active key '
            'of the requested user before running, so the flow has a key to deactivate')
    if owner != 'same-user':
        raise AssertionError(
            'the access key stored in Jenkins is not a key of the requested IAM user; '
            'check that username and the Jenkins credential belong together')


def _access_key_status(iam_client, username: str, access_key_id: str) -> str:
    """Returns the IAM status of an access key, or 'missing' when it no longer exists."""
    metadata = _run_aws_call(iam_client.list_access_keys,
                             UserName=username)['AccessKeyMetadata']
    for key in metadata:
        if key['AccessKeyId'] == access_key_id:
            return key['Status']
    return 'missing'


def _ensure_rotation_preconditions(iam_client, previous_access_key: str):
    """
    Runs the production precondition helper so the test and the policy share the same logic:
    the key stored in Jenkins must be Active and a different inactive key must exist for the
    policy to consume. Skips when the state cannot be reached safely.
    """
    try:
        ensure_rotation_preconditions(SimpleNamespace(get_iam_client=iam_client), REAL_USER,
                                      previous_access_key)
    except JenkinsOperationsError as err:
        pytest.skip(str(err))


def _access_key_owner(iam_client, username: str, access_key_id: str) -> str:
    """
    Classifies the key without exposing ids: 'same-user', 'missing' or 'error:<code>'. A key
    that is not listed for the user has either been deleted or belongs to another user; the
    rotation stops in both cases. ListAccessKeys is used because iam:GetAccessKeyLastUsed is
    often not granted, while listing is needed by the flow anyway.
    """
    try:
        metadata = iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        return f'error:{code}'
    return 'same-user' if any(key['AccessKeyId'] == access_key_id for key in metadata) \
        else 'missing'


def _assert_not_logged(caplog, values):
    for value in values:
        if value and value in caplog.text:
            raise AssertionError('a sensitive value was written to the log')


@pytest.mark.skipif(
    not TEMP_USER_E2E_ENABLED,
    reason='set JENKINS_TEMP_USER_E2E=yes to run the temporary-user rotation flow')
def test_rotation_to_jenkins_with_temp_user(tmp_path, caplog):
    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    client = _jenkins_client()
    username = f'integration-rotate-{uuid.uuid4().hex[:12]}'
    credentials_file = tmp_path / 'iam_credentials.json'
    access_key_credential_id = f'integration-rotation-access-key-{uuid.uuid4().hex[:12]}'
    secret_key_credential_id = f'integration-rotation-secret-key-{uuid.uuid4().hex[:12]}'
    previous_access_key = f'old-access-key-{uuid.uuid4().hex}'
    previous_secret_key = f'old-secret-{uuid.uuid4().hex}'

    try:
        _run_aws_call(iam_client.create_user, UserName=username,
                      Tags=[{'Key': 'User', 'Value': 'integration'}])
        _create_inactive_key(iam_client, username)

        _reset_policy_environment()
        _set_policy_environment(username, credentials_file)
        client.create_secret(access_key_credential_id, previous_access_key)
        client.create_secret(secret_key_credential_id, previous_secret_key)

        with caplog.at_level(logging.INFO, logger='cloud_governance'):
            assert len(_run_rotation_policy()) == 1
            credentials = load_rotated_credentials(str(credentials_file))

            result = publish_rotated_credentials(
                client, credentials,
                access_key_credential_id=access_key_credential_id,
                secret_access_key_credential_id=secret_key_credential_id)

        _assert_equal(result['access_key_to_inactive'], previous_access_key,
                      'the previous access key id was not captured')
        _assert_equal(client.read_secret(access_key_credential_id), credentials['access_key_id'],
                      'read_secret did not return the rotated access key id')
        _assert_equal(client.read_secret(secret_key_credential_id),
                      credentials['secret_access_key'],
                      'read_secret did not return the rotated secret access key')
        _assert_not_logged(caplog, (username, previous_access_key, previous_secret_key,
                                    credentials['access_key_id'],
                                    credentials['secret_access_key'],
                                    os.environ.get('AWS_ACCESS_KEY_ID'),
                                    os.environ.get('AWS_SECRET_ACCESS_KEY')))
    finally:
        _reset_policy_environment()
        for credential_id in (access_key_credential_id, secret_key_credential_id):
            try:
                client.delete_secret(credential_id)
            except Exception:
                pass
        _delete_iam_user(iam_client, username)


@pytest.mark.skipif(not REAL_USER, reason='set username=<iam-user> to rotate a real account key')
def test_rotate_real_user_and_publish(tmp_path, caplog):
    if not (REAL_USER_CONFIRMED and REAL_CREDENTIALS_CONFIRMED):
        pytest.skip('set IAM_ROTATE_TEST_CONFIRM=yes and JENKINS_REAL_CREDENTIALS_CONFIRM=yes')

    iam_client = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
    client = _jenkins_client()
    credentials_file = tmp_path / 'iam_credentials.json'
    access_key_credential_id, secret_access_key_credential_id = get_default_credential_ids()
    previous_access_key = client.read_secret(access_key_credential_id)

    # Fail before rotating or publishing if the Jenkins credential and username do not describe
    # the same IAM user: publishing would silently move the pipelines to another account, and the
    # deactivation call would target a key this user cannot see.
    _assert_jenkins_key_belongs_to_user(iam_client, REAL_USER, previous_access_key)

    # The Jenkins key must be Active and only ever deactivated; a different inactive key is the
    # one the policy consumes.
    _ensure_rotation_preconditions(iam_client, previous_access_key)

    try:
        _reset_policy_environment()
        _set_policy_environment(REAL_USER, credentials_file)

        with caplog.at_level(logging.INFO, logger='cloud_governance'):
            assert len(_run_rotation_policy()) == 1
            credentials = load_rotated_credentials(str(credentials_file))
            # Runs the production path: publish to Jenkins, record access_key_to_inactive in the
            # credentials file, then deactivate the previous key with the new Jenkins credentials.
            result = rotate_and_publish_to_jenkins(
                str(credentials_file), client, region_name=AWS_DEFAULT_REGION,
                access_key_credential_id=access_key_credential_id,
                secret_access_key_credential_id=secret_access_key_credential_id)

        _assert_equal(result['access_key_to_inactive'], previous_access_key,
                      'the previous access key id was not captured')
        _assert_equal(client.read_secret(access_key_credential_id),
                      credentials['access_key_id'],
                      'read_secret did not return the rotated access key id')
        _assert_equal(client.read_secret(secret_access_key_credential_id),
                      credentials['secret_access_key'],
                      'read_secret did not return the rotated secret access key')
        _assert_equal(load_rotated_credentials(str(credentials_file)).get(
            'access_key_to_inactive'), result['access_key_to_inactive'],
            'access_key_to_inactive was not recorded in the credentials file')
        # When the caller is the key stored in Jenkins (self-rotation), that key was just
        # deactivated; the post-run checks therefore use the newly published credentials.
        verification_client = _iam_client_with_credentials(
            client.read_secret(access_key_credential_id),
            client.read_secret(secret_access_key_credential_id))
        # The key stored in Jenkins is only ever deactivated, never deleted by the rotation.
        _assert_equal(
            _access_key_status(verification_client, REAL_USER,
                               result['access_key_to_inactive']),
            'Inactive', 'the previous access key was not deactivated')
        _assert_equal(
            _access_key_status(verification_client, REAL_USER, credentials['access_key_id']),
            'Active', 'the rotated access key is not Active')
        # The flow leaves the rotated key as the only Active key, except for the caller's own
        # key when the credentials running this test belong to the target user.
        allowed_active_keys = {credentials['access_key_id']}
        caller_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        if caller_key_id:
            allowed_active_keys.add(caller_key_id)
        final_active_keys = {key['AccessKeyId'] for key in _run_aws_call(
            verification_client.list_access_keys, UserName=REAL_USER)['AccessKeyMetadata']
            if key['Status'] == 'Active'}
        if final_active_keys - allowed_active_keys:
            raise AssertionError('a stale access key is still Active after the rotation')
        if credentials['access_key_id'] not in final_active_keys:
            raise AssertionError('the rotated access key is not Active after the rotation')

        _assert_not_logged(caplog, (REAL_USER, previous_access_key,
                                    credentials['access_key_id'],
                                    credentials['secret_access_key'],
                                    os.environ.get('AWS_ACCESS_KEY_ID'),
                                    os.environ.get('AWS_SECRET_ACCESS_KEY')))
    finally:
        _reset_policy_environment()
