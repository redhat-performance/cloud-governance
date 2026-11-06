"""
Policy to rotate an inactive IAM access key for a single user.

If the user has an access key with Status == 'Inactive', the key is deleted and a new
one is created. The new credentials are written to IAM_CREDENTIALS_FILE.

Set IAM_PUBLISH_TO_JENKINS=true to run the full flow in this process, as the integration test
does: the key stored in Jenkins is kept Active (or reactivated) and never consumed, an inactive
key is prepared when needed, the new key is published to Jenkins, and the key Jenkins held before
the switch is deactivated. In that mode the credentials are handed from memory to Jenkins and
are never written to disk, so no local secret file exists. IAM_CREDENTIALS_FILE is ignored.

Without IAM_PUBLISH_TO_JENKINS the new credentials are written to IAM_CREDENTIALS_FILE for a
separate publish step. That file is never created implicitly: when neither a destination nor a
file is configured, a live rotation is skipped, because the new secret would have nowhere to go.
"""
import json
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.jenkins.rotated_credentials import (
    ensure_rotation_preconditions,
    get_default_credential_ids,
    get_jenkins_client,
    is_publish_to_jenkins_enabled,
    rotate_and_publish_credentials,
)
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations

# IAM is global, but PolicyRunner instantiates the policy once per active region. Remember users
# rotated in this process so a second region cannot rotate another key and overwrite the
# credentials file.
_ROTATED_USERS = set()


class RotateAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "Rotate"
    # A freshly created access key is eventually consistent in STS: give it up to ~15s.
    VERIFY_ATTEMPTS = 5
    VERIFY_DELAY_SECONDS = 3

    @property
    def credentials_file(self) -> str:
        """
        Returns the explicitly configured IAM_CREDENTIALS_FILE, or an empty string. No file is
        ever created implicitly: with IAM_PUBLISH_TO_JENKINS the secret goes from memory to
        Jenkins, and without either setting a live rotation is skipped.
        :return: Configured credentials file path, or ''.
        """
        return (self._environment_variables_dict.get('IAM_CREDENTIALS_FILE') or '').strip()

    def _log_new_key_connectivity(self, access_key_id: str, secret_access_key: str):
        """
        Connects to AWS with the newly created access key and logs the outcome.
        A brand new key can take a moment to propagate, so retry a few times.
        Never raises: the rotation already happened and the credentials are stored.
        Deliberately logs neither the user, the key nor the account.
        :param access_key_id: The new access key ID.
        :param secret_access_key: The new secret access key.
        """
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=self._region,
        )
        for attempt in range(1, self.VERIFY_ATTEMPTS + 1):
            try:
                session.client('sts').get_caller_identity()
            except ClientError as err:
                error_code = err.response.get('Error', {}).get('Code')
                if error_code != 'InvalidClientTokenId' or attempt == self.VERIFY_ATTEMPTS:
                    if error_code == 'InvalidClientTokenId':
                        logger.warning(f"The newly created access key was not accepted by STS after "
                                       f"{attempt} attempts (~{attempt * self.VERIFY_DELAY_SECONDS}s); "
                                       f"AWS keys can take several seconds to propagate. Verify it manually.")
                    else:
                        # A ClientError message contains the caller ARN and account id; log the
                        # error code only.
                        logger.warning(f"Unable to connect to AWS with the newly created access key "
                                       f"after {attempt} attempt(s) ({error_code})")
                    return
                time.sleep(self.VERIFY_DELAY_SECONDS)
                continue
            except Exception as err:
                logger.warning(f"Unable to connect to AWS with the newly created access key "
                               f"({type(err).__name__})")
                return
            logger.info("Successfully connected to AWS with the newly created access key")
            return

    def _build_credentials_payload(self, username: str, access_key_id: str,
                                   secret_access_key: str) -> dict:
        """
        Builds the payload shared by the file and the in-memory publish paths.
        :param username: IAM user name.
        :param access_key_id: The new access key ID.
        :param secret_access_key: The new secret access key.
        :return: The credentials payload.
        """
        return {
            'username': username,
            'access_key_id': access_key_id,
            'secret_access_key': secret_access_key,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

    def _store_credentials(self, payload: dict):
        """
        Writes the new credentials to the credentials file (0600, atomically). Called only when
        the credentials must be handed to a separate publish step.
        :param payload: Return value of _build_credentials_payload.
        """
        credentials_file = self.credentials_file
        tmp_file = f'{credentials_file}.tmp'
        try:
            with open(tmp_file, 'w') as file:
                json.dump(payload, file)
            os.chmod(tmp_file, 0o600)
            os.replace(tmp_file, credentials_file)
            logger.info(f"Stored the new credentials in {credentials_file}")
        except Exception as err:
            logger.error(f"Failed to store the new credentials: {err}")
            raise err

    def _get_last_activity_days(self, access_key_id: str, age_days: int):
        """
        Returns the days since the key was last used, falling back to its age when it was never
        used or the lookup fails. Never logs the key id or a ClientError message, which contains
        the caller ARN and account id.
        :param access_key_id: The inactive access key id.
        :param age_days: Age of the key, used when there is no last-used date.
        :return: Days since last use, or None when the lookup failed.
        """
        try:
            last_used_date = self._iam_operations.get_iam_client.get_access_key_last_used(
                AccessKeyId=access_key_id).get('AccessKeyLastUsed', {}).get('LastUsedDate')
            return self.calculate_days(create_date=last_used_date) if last_used_date \
                else age_days
        except ClientError as err:
            error_code = err.response.get('Error', {}).get('Code', 'unknown')
            logger.error(f"Failed to get the last used date of the inactive access key "
                         f"({error_code}); last_activity_days will be empty")
        except Exception as err:
            logger.error(f"Failed to get the last used date of the inactive access key "
                         f"({type(err).__name__}); last_activity_days will be empty")
        return None

    def _prepare_jenkins_publishing(self, username: str):
        """
        Prepares the full-flow state: the key stored in Jenkins must be Active and a different
        inactive key must be available for the rotation to consume.
        :param username: IAM user name.
        :return: (client, access key credential id, secret credential id) or None on failure.
        """
        try:
            jenkins_client = get_jenkins_client()
            access_key_credential_id, secret_access_key_credential_id = \
                get_default_credential_ids()
            jenkins_access_key_id = jenkins_client.read_secret(access_key_credential_id)
            ensure_rotation_preconditions(self._iam_operations, username,
                                          jenkins_access_key_id)
        except JenkinsOperationsError as err:
            logger.error(f'rotate_access_key: cannot publish to Jenkins: {err}')
            return None
        return jenkins_client, access_key_credential_id, secret_access_key_credential_id

    def _destination_is_available(self, publish_to_jenkins: bool) -> bool:
        """
        A live rotation needs somewhere to deliver the new secret: Jenkins, or an explicitly
        configured credentials file. A dry run creates no secret, so it needs none. Never falls
        back to an implicit local file.
        :param publish_to_jenkins: Whether the in-process Jenkins publish is enabled.
        :return: True when the rotation may proceed.
        """
        if self._dry_run != 'no' or publish_to_jenkins or self.credentials_file:
            return True
        logger.error('rotate_access_key: no destination for the new credentials; set '
                     'IAM_PUBLISH_TO_JENKINS=yes, or IAM_CREDENTIALS_FILE for a separate '
                     'publish step. Skipping the rotation')
        return False

    def _deliver_credentials(self, publish_to_jenkins: bool, jenkins_publishing,
                             username: str, credentials: tuple):
        """
        Hands the new credentials to the configured destination: Jenkins (in memory) or the
        explicitly configured credentials file.
        :param publish_to_jenkins: Whether the in-process Jenkins publish is enabled.
        :param jenkins_publishing: Return value of _prepare_jenkins_publishing.
        :param username: IAM user name.
        :param credentials: (AccessKeyId, SecretAccessKey) returned by the rotation.
        """
        payload = self._build_credentials_payload(username, *credentials)
        if publish_to_jenkins:
            # The secret goes from this process straight to Jenkins. IAM_CREDENTIALS_FILE is
            # deliberately ignored so the credentials never exist as a local file.
            if self._environment_variables_dict.get('IAM_CREDENTIALS_FILE'):
                logger.info('rotate_access_key: IAM_CREDENTIALS_FILE is ignored when '
                            'IAM_PUBLISH_TO_JENKINS is enabled, so the secret stays in memory')
            self._publish_credentials_to_jenkins(jenkins_publishing, payload)
        else:
            self._store_credentials(payload)
        self._log_new_key_connectivity(*credentials)

    def _publish_credentials_to_jenkins(self, jenkins_publishing: tuple, credentials: dict):
        """
        Publishes the credentials straight from memory to Jenkins and deactivates the key
        Jenkins held before the switch. Nothing is written to disk on this path.
        :param jenkins_publishing: Return value of _prepare_jenkins_publishing.
        :param credentials: Return value of _build_credentials_payload.
        """
        jenkins_client, access_key_credential_id, secret_access_key_credential_id = \
            jenkins_publishing
        try:
            rotate_and_publish_credentials(
                credentials, jenkins_client, region_name=self._region,
                access_key_credential_id=access_key_credential_id,
                secret_access_key_credential_id=secret_access_key_credential_id,
                iam_operations=self._iam_operations)
            logger.info('Published the rotated credentials to Jenkins')
        except JenkinsOperationsError as err:
            logger.error(f'rotate_access_key: failed to publish the rotated credentials: {err}')
            raise

    def run_policy_operations(self):
        """
        Rotates the oldest inactive access key of the user given by the `username` env var.
        Returns a single ES row describing the rotation, or an empty list when there is
        nothing to do.
        """
        username = (self._environment_variables_dict.get('username') or '').strip()
        if not username:
            logger.warning('rotate_access_key: username is not set, skipping')
            return []
        if username in _ROTATED_USERS:
            logger.info("rotate_access_key: already rotated in this run, skipping")
            return []

        tags = self._iam_operations.get_user_tags(username=username)
        if self.get_skip_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
            logger.info("rotate_access_key: the user is marked to skip, skipping")
            return []

        # When publishing is enabled the policy runs the same flow as the integration test:
        # the key stored in Jenkins must stay Active (it is only deactivated after the switch)
        # and a different inactive key must be available for the policy to consume.
        publish_to_jenkins = is_publish_to_jenkins_enabled() and self._dry_run == 'no'
        if not self._destination_is_available(publish_to_jenkins):
            return []
        jenkins_publishing = None
        if publish_to_jenkins:
            jenkins_publishing = self._prepare_jenkins_publishing(username)
            if jenkins_publishing is None:
                return []

        inactive_keys = self._iam_operations.get_inactive_access_keys(username=username)
        if not inactive_keys:
            logger.info("rotate_access_key: no inactive access key found")
            return []

        oldest_inactive_key = inactive_keys[0]
        access_key_id = oldest_inactive_key['AccessKeyId']
        age_days = self.calculate_days(create_date=oldest_inactive_key['CreateDate'])
        last_activity_days = self._get_last_activity_days(access_key_id, age_days)

        _ROTATED_USERS.add(username)
        credentials = self._iam_operations.rotate_user_access_key(username=username,
                                                                  dry_run=self._dry_run != 'no')
        if credentials:
            self._deliver_credentials(publish_to_jenkins, jenkins_publishing, username,
                                      credentials)

        resource_data = self._get_es_schema(
            resource_id=username,
            user=self.get_tag_name_from_tags(tags=tags, tag_name='User') or username,
            email=self.get_tag_name_from_tags(tags=tags, tag_name='Email'),
            skip_policy=self.get_skip_policy_value(tags=tags),
            cleanup_days=0,
            dry_run=self._dry_run,
            name=username,
            region=self._region,
            cleanup_result=str(bool(credentials)),
            resource_action=self.RESOURCE_ACTION,
            cloud_name=self._cloud_name,
            resource_type='AccessKeyRotation',
            resource_state='Inactive',
            age_days=age_days,
            last_activity_days=last_activity_days,
            unit_price=0,
        )
        return [resource_data]
