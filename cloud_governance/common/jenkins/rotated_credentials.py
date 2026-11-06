"""
Publishes the credentials produced by the rotate_access_key policy into Jenkins.

RotateAccessKey writes {'username', 'access_key_id', 'secret_access_key', 'created_at'} to
IAM_CREDENTIALS_FILE. This module reads that file, captures the access key id currently stored in
Jenkins, and replaces the two Jenkins secret-text credentials used by the pipelines.

The captured id is returned as ``access_key_to_inactive``: it is the key that was active before
the switch. ``rotate_and_publish_to_jenkins`` records it in the credentials file, so the
deactivation can be retried after a restart, then disables it in AWS by authenticating with the
new key read back from Jenkins. Secrets, key ids, usernames and credential ids are never logged.

The rotate_access_key policy runs this module itself when IAM_PUBLISH_TO_JENKINS is enabled:
it prepares the IAM state (the Jenkins key stays Active, a different inactive key is consumed),
rotates, publishes the new key and deactivates the previous one in a single process. That path
uses ``rotate_and_publish_credentials`` and never writes the secret to disk.

The file-based functions are for a publish that runs in a separate process, and only that
caller writes a file. RotateAccessKey itself never creates one implicitly.
"""
import json
import os

from botocore.exceptions import ClientError

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.jenkins.jenkins_operations import JenkinsOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables

DEFAULT_ACCESS_KEY_CREDENTIAL_ID = 'EBATTAT_AWS_ACCESS_KEY_ID'
DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID = 'EBATTAT_AWS_SECRET_ACCESS_KEY'
PUBLISH_ENVIRONMENT_VARIABLE = 'IAM_PUBLISH_TO_JENKINS'
REQUIRED_FIELDS = ('username', 'access_key_id', 'secret_access_key')


def get_default_credential_ids() -> tuple:
    """
    Resolves the Jenkins credential ids to publish to. JENKINS_ACCESS_KEY_CREDENTIAL_ID and
    JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID override the EBATTAT_* defaults; blank values fall
    back to the defaults.
    :return: (access key credential id, secret access key credential id)
    """
    env = environment_variables.environment_variables_dict
    access_key_credential_id = (env.get('JENKINS_ACCESS_KEY_CREDENTIAL_ID') or '').strip()
    secret_access_key_credential_id = \
        (env.get('JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID') or '').strip()
    return (access_key_credential_id or DEFAULT_ACCESS_KEY_CREDENTIAL_ID,
            secret_access_key_credential_id or DEFAULT_SECRET_ACCESS_KEY_CREDENTIAL_ID)


def is_publish_to_jenkins_enabled() -> bool:
    """
    :return: True when IAM_PUBLISH_TO_JENKINS is enabled.
    """
    return bool(environment_variables.environment_variables_dict.get(
        PUBLISH_ENVIRONMENT_VARIABLE, False))


def get_jenkins_client() -> JenkinsOperations:
    """
    Builds a Jenkins client that can read and write secret-text credentials. Fails before any
    AWS key is rotated when the Jenkins connection settings are incomplete, so a rotation can
    never silently end up in the rotate-only state.
    :return: JenkinsOperations with Script Console reads enabled.
    """
    env = environment_variables.environment_variables_dict
    has_auth = env.get('JENKINS_API_TOKEN') or env.get('JENKINS_PASSWORD')
    if not (env.get('JENKINS_URL') and env.get('JENKINS_USERNAME') and has_auth):
        raise JenkinsOperationsError(
            'JENKINS_URL, JENKINS_USERNAME and JENKINS_API_TOKEN or JENKINS_PASSWORD must be '
            'configured to publish rotated credentials')
    return JenkinsOperations(allow_script_console=True)


def _list_access_key_metadata(iam_operations, username: str) -> list:
    """
    Lists the user's access keys. Error messages never echo the user or a key id.
    :param iam_operations: IAMOperations instance.
    :param username: IAM user name.
    :return: AccessKeyMetadata list.
    """
    try:
        return iam_operations.get_iam_client.list_access_keys(
            UserName=username)['AccessKeyMetadata']
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        raise JenkinsOperationsError(
            f'Failed to list the access keys needed by the rotation ({code})') from None


def _update_access_key_status(iam_operations, username: str, access_key_id: str, status: str):
    """
    Sets an access key Active or Inactive. Error messages never echo the user or a key id.
    :param iam_operations: IAMOperations instance.
    :param username: IAM user name.
    :param access_key_id: Access key id to update.
    :param status: 'Active' or 'Inactive'.
    """
    try:
        iam_operations.get_iam_client.update_access_key(
            UserName=username, AccessKeyId=access_key_id, Status=status)
    except ClientError as err:
        code = err.response.get('Error', {}).get('Code', 'unknown')
        raise JenkinsOperationsError(
            f'Failed to set an access key to {status} for the rotation ({code})') from None


def ensure_jenkins_key_is_active(iam_operations, username: str, access_key_id: str):
    """
    Guarantees the rotation cannot consume the key stored in Jenkins: the key must belong to the
    user, and an Inactive Jenkins key is reactivated. This mirrors the integration test, where
    the Jenkins key is only ever deactivated by the publish step and never deleted.

    Note: a reactivated key is active again, so callers must intend to keep using it until the
    publish step deactivates it.
    :param iam_operations: IAMOperations instance.
    :param username: IAM user name.
    :param access_key_id: Access key id currently stored in Jenkins.
    """
    statuses = {key['AccessKeyId']: key['Status']
                for key in _list_access_key_metadata(iam_operations, username)}
    if access_key_id not in statuses:
        raise JenkinsOperationsError(
            'The access key stored in Jenkins does not exist for the requested user; update the '
            'Jenkins credentials with a live Active key of that user before rotating')
    if statuses[access_key_id] == 'Inactive':
        _update_access_key_status(iam_operations, username, access_key_id, 'Active')
        logger.info('Reactivated the inactive access key stored in Jenkins')


def prepare_inactive_key(iam_operations, username: str, keep_access_key_id: str) -> bool:
    """
    Makes the rotation runnable when no inactive key exists, mirroring the integration test.
    Deactivates a stale Active key, or creates and immediately deactivates a new key when the
    user has a free slot. Never touches the key stored in Jenkins or the caller's own key.
    Key ids and the created secret are never logged.
    :param iam_operations: IAMOperations instance.
    :param username: IAM user name.
    :param keep_access_key_id: The key stored in Jenkins; never deactivated here.
    :return: True when an inactive key exists afterwards, False when no safe candidate exists.
    """
    metadata = _list_access_key_metadata(iam_operations, username)
    if any(key['Status'] == 'Inactive' for key in metadata):
        return True
    active_keys = [key['AccessKeyId'] for key in metadata if key['Status'] == 'Active']
    caller_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    # Without the caller's key id there is no way to tell its key apart from a stale one, so
    # never deactivate an Active key in that case: it could invalidate the running credentials.
    stale_keys = [key_id for key_id in active_keys
                  if key_id not in (keep_access_key_id, caller_key_id)] \
        if caller_key_id else []
    if stale_keys:
        for key_id in stale_keys:
            _update_access_key_status(iam_operations, username, key_id, 'Inactive')
        logger.info('Deactivated a stale access key to prepare the rotation')
        return True
    if len(active_keys) == 1:
        try:
            new_key_id = iam_operations.get_iam_client.create_access_key(
                UserName=username)['AccessKey']['AccessKeyId']
        except ClientError as err:
            code = err.response.get('Error', {}).get('Code', 'unknown')
            raise JenkinsOperationsError(
                f'Failed to create the access key needed by the rotation ({code})') from None
        _update_access_key_status(iam_operations, username, new_key_id, 'Inactive')
        logger.info('Created and deactivated a key to prepare the rotation')
        return True
    return False


def ensure_rotation_preconditions(iam_operations, username: str, jenkins_access_key_id: str):
    """
    Guarantees the starting state required by the full flow: the key stored in Jenkins is Active
    and a different inactive key exists for the policy to consume.
    :param iam_operations: IAMOperations instance.
    :param username: IAM user name.
    :param jenkins_access_key_id: Access key id currently stored in Jenkins.
    """
    ensure_jenkins_key_is_active(iam_operations, username, jenkins_access_key_id)
    if not prepare_inactive_key(iam_operations, username, jenkins_access_key_id):
        raise JenkinsOperationsError(
            'The user has no inactive access key and no free slot to prepare one; the key stored '
            'in Jenkins and the caller key occupy both slots. Run with credentials of another '
            'identity so a different key can be consumed by the rotation')


def validate_rotated_credentials(credentials: dict) -> dict:
    """
    Validates the payload written by RotateAccessKey. Error messages never echo the values.
    :param credentials: Parsed JSON payload.
    :return: The payload unchanged.
    """
    if not isinstance(credentials, dict):
        raise JenkinsOperationsError('The rotated credentials payload must be a JSON object')
    for field in REQUIRED_FIELDS:
        value = credentials.get(field)
        if not isinstance(value, str) or not value.strip():
            raise JenkinsOperationsError(
                f'The rotated credentials file is missing a valid {field}')
    return credentials


def load_rotated_credentials(credentials_file: str) -> dict:
    """
    Reads and validates the JSON file written by the rotate_access_key policy.
    :param credentials_file: Path of IAM_CREDENTIALS_FILE.
    :return: The validated payload.
    """
    if not isinstance(credentials_file, str) or not credentials_file.strip():
        raise JenkinsOperationsError(
            'The rotated credentials file path must be a non-empty string')
    try:
        with open(credentials_file) as file:
            payload = json.load(file)
    except FileNotFoundError:
        raise JenkinsOperationsError('The rotated credentials file was not found') from None
    except (json.JSONDecodeError, OSError):
        raise JenkinsOperationsError('The rotated credentials file could not be read') from None
    return validate_rotated_credentials(payload)


def publish_rotated_credentials(client, credentials: dict,
                                access_key_credential_id: str = None,
                                secret_access_key_credential_id: str = None) -> dict:
    """
    Replaces the access key id and secret access key credentials in Jenkins.

    The current access key id is read before anything is written and returned as
    ``access_key_to_inactive``; pass the result to deactivate_previous_access_key to disable it.

    :param client: JenkinsOperations instance with allow_script_console=True.
    :param credentials: Payload returned by load_rotated_credentials.
    :param access_key_credential_id: Jenkins credential id holding the access key id. Defaults to
        JENKINS_ACCESS_KEY_CREDENTIAL_ID, then EBATTAT_AWS_ACCESS_KEY_ID.
    :param secret_access_key_credential_id: Jenkins credential id holding the secret access key.
        Defaults to JENKINS_SECRET_ACCESS_KEY_CREDENTIAL_ID, then EBATTAT_AWS_SECRET_ACCESS_KEY.
    :return: {'username': ..., 'access_key_to_inactive': <previous access key id>}
    """
    validate_rotated_credentials(credentials)
    default_access_key_id, default_secret_access_key_id = get_default_credential_ids()
    access_key_credential_id = access_key_credential_id or default_access_key_id
    secret_access_key_credential_id = \
        secret_access_key_credential_id or default_secret_access_key_id
    access_key_to_inactive = client.read_secret(access_key_credential_id)
    client.write_secret(access_key_credential_id, credentials['access_key_id'])
    logger.info('Updated the Jenkins access key credential')
    client.write_secret(secret_access_key_credential_id, credentials['secret_access_key'])
    logger.info('Updated the Jenkins secret access key credential')
    return {
        'username': credentials['username'],
        'access_key_to_inactive': access_key_to_inactive,
    }


def update_rotated_credentials(credentials_file: str, updates: dict) -> dict:
    """
    Merges fields into the JSON file written by RotateAccessKey, atomically and keeping 0600.
    ``rotate_and_publish_to_jenkins`` uses it to record access_key_to_inactive, so the
    deactivation step can be retried after a restart. Values are never logged.
    :param credentials_file: Path of IAM_CREDENTIALS_FILE.
    :param updates: Fields to add or replace.
    :return: The updated payload.
    """
    if not isinstance(updates, dict):
        raise JenkinsOperationsError('The rotated credentials updates must be a dict')
    credentials = load_rotated_credentials(credentials_file)
    credentials.update(updates)
    tmp_file = f'{credentials_file}.tmp'
    try:
        with open(tmp_file, 'w') as file:
            json.dump(credentials, file)
        os.chmod(tmp_file, 0o600)
        os.replace(tmp_file, credentials_file)
    except OSError:
        raise JenkinsOperationsError('The rotated credentials file could not be updated') from None
    return credentials


def _validate_publish_result(result: dict) -> dict:
    """
    Validates the dict returned by publish_rotated_credentials. Error messages never echo values.
    :param result: The publish result.
    :return: The result unchanged.
    """
    if not isinstance(result, dict):
        raise JenkinsOperationsError('The publish result must be a dict')
    for field in ('username', 'access_key_to_inactive'):
        value = result.get(field)
        if not isinstance(value, str) or not value.strip():
            raise JenkinsOperationsError(f'The publish result is missing a valid {field}')
    return result


def deactivate_previous_access_key(client, result: dict, region_name: str = None,
                                   access_key_credential_id: str = None,
                                   secret_access_key_credential_id: str = None,
                                   iam_operations=None, deactivate_stale_keys: bool = True):
    """
    Deactivates ``result['access_key_to_inactive']``, authenticating with the credentials that
    were just published to Jenkins. The new access key id and secret are read back from Jenkins,
    so the call also proves the stored values are usable.

    When ``deactivate_stale_keys`` is True (the default), any other Active key of the user is
    deactivated too, so a run always ends with exactly one Active key: the one just published.
    :param client: JenkinsOperations instance with allow_script_console=True.
    :param result: Return value of publish_rotated_credentials.
    :param region_name: IAM client region. Defaults to AWS_DEFAULT_REGION.
    :param access_key_credential_id: Jenkins credential id holding the new access key id.
    :param secret_access_key_credential_id: Jenkins credential id holding the new secret.
    :param iam_operations: IAMOperations instance; a default one is created when omitted.
    :param deactivate_stale_keys: Also deactivate any other Active key of the user.
    """
    _validate_publish_result(result)
    default_access_key_id, default_secret_access_key_id = get_default_credential_ids()
    access_key_credential_id = access_key_credential_id or default_access_key_id
    secret_access_key_credential_id = \
        secret_access_key_credential_id or default_secret_access_key_id
    new_access_key_id = client.read_secret(access_key_credential_id)
    new_secret_access_key = client.read_secret(secret_access_key_credential_id)
    region_name = region_name or environment_variables.environment_variables_dict.get(
        'AWS_DEFAULT_REGION')
    if iam_operations is None:
        iam_operations = IAMOperations()
    iam_operations.deactivate_access_key_with_credentials(
        username=result['username'],
        access_key_id=result['access_key_to_inactive'],
        aws_access_key_id=new_access_key_id,
        aws_secret_access_key=new_secret_access_key,
        region_name=region_name,
    )
    if deactivate_stale_keys:
        iam_operations.deactivate_stale_active_keys(
            username=result['username'],
            keep_access_key_id=new_access_key_id,
            aws_access_key_id=new_access_key_id,
            aws_secret_access_key=new_secret_access_key,
            region_name=region_name,
        )
    logger.info('Deactivated the previous access key with the new credentials')


def rotate_and_publish_credentials(credentials: dict, client, region_name: str = None,
                                   access_key_credential_id: str = None,
                                   secret_access_key_credential_id: str = None,
                                   iam_operations=None,
                                   deactivate_stale_keys: bool = True) -> dict:
    """
    Runs the post-rotation steps entirely in memory: publish the already-issued credentials to
    Jenkins, then deactivate the key Jenkins held before the switch. No secret is written to
    disk, so this is the path used by the policy when IAM_PUBLISH_TO_JENKINS is enabled.

    A crash between the publish and the deactivation leaves the previous key Active; the next
    run deactivates it through the normal precondition and stale-key cleanup.
    :param credentials: Payload with username, access_key_id and secret_access_key.
    :param client: JenkinsOperations instance with allow_script_console=True.
    :return: The publish result, {'username', 'access_key_to_inactive'}.
    """
    validate_rotated_credentials(credentials)
    result = publish_rotated_credentials(
        client, credentials,
        access_key_credential_id=access_key_credential_id,
        secret_access_key_credential_id=secret_access_key_credential_id)
    deactivate_previous_access_key(
        client, result, region_name=region_name,
        access_key_credential_id=access_key_credential_id,
        secret_access_key_credential_id=secret_access_key_credential_id,
        iam_operations=iam_operations,
        deactivate_stale_keys=deactivate_stale_keys)
    return result


def rotate_and_publish_to_jenkins(credentials_file: str, client, region_name: str = None,
                                  access_key_credential_id: str = None,
                                  secret_access_key_credential_id: str = None,
                                  iam_operations=None,
                                  deactivate_stale_keys: bool = True) -> dict:
    """
    Runs the post-rotation steps end to end: load the credentials file written by
    RotateAccessKey, publish the new values to Jenkins, record access_key_to_inactive in that
    file, then deactivate the key Jenkins held before the switch (and, by default, any other
    Active key of the user).
    :param credentials_file: Path of IAM_CREDENTIALS_FILE.
    :param client: JenkinsOperations instance with allow_script_console=True.
    :return: The publish result, {'username', 'access_key_to_inactive'}.
    """
    credentials = load_rotated_credentials(credentials_file)
    result = publish_rotated_credentials(
        client, credentials,
        access_key_credential_id=access_key_credential_id,
        secret_access_key_credential_id=secret_access_key_credential_id)
    update_rotated_credentials(
        credentials_file, {'access_key_to_inactive': result['access_key_to_inactive']})
    deactivate_previous_access_key(
        client, result, region_name=region_name,
        access_key_credential_id=access_key_credential_id,
        secret_access_key_credential_id=secret_access_key_credential_id,
        iam_operations=iam_operations,
        deactivate_stale_keys=deactivate_stale_keys)
    return result
