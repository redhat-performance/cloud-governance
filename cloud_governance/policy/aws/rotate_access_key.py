"""
Policy to rotate an inactive IAM access key for a single user.

If the user has an access key with Status == 'Inactive', the key is deleted and a new
one is created. The new credentials are written to a local JSON file.
"""
import json
import os
from datetime import datetime, timezone

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations

# IAM is global, but PolicyRunner instantiates the policy once per active region. Remember users
# rotated in this process so a second region cannot rotate another key and overwrite the
# credentials file.
_ROTATED_USERS = set()


class RotateAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "Rotate"
    DEFAULT_CREDENTIALS_FILE = "/tmp/iam_credentials.json"

    def _store_credentials(self, username: str, access_key_id: str, secret_access_key: str):
        """
        Writes the new credentials to IAM_CREDENTIALS_FILE (0600, atomically).
        This is the single place to change when the credentials are pushed to Jenkins later.
        :param username: IAM user name.
        :param access_key_id: The new access key ID.
        :param secret_access_key: The new secret access key.
        """
        credentials_file = self._environment_variables_dict.get(
            'IAM_CREDENTIALS_FILE') or self.DEFAULT_CREDENTIALS_FILE
        payload = {
            'username': username,
            'access_key_id': access_key_id,
            'secret_access_key': secret_access_key,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        tmp_file = f'{credentials_file}.tmp'
        try:
            with open(tmp_file, 'w') as file:
                json.dump(payload, file)
            os.chmod(tmp_file, 0o600)
            os.replace(tmp_file, credentials_file)
            logger.info(f"Stored credentials of access key '{access_key_id}' for user '{username}' "
                        f"in {credentials_file}")
        except Exception as err:
            logger.error(f"Failed to store credentials for user '{username}': {err}")
            raise err

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
            logger.info(f"rotate_access_key: user '{username}' already rotated in this run, skipping")
            return []

        tags = self._iam_operations.get_user_tags(username=username)
        if self.get_skip_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
            logger.info(f"rotate_access_key: user '{username}' is marked to skip, skipping")
            return []

        inactive_keys = self._iam_operations.get_inactive_access_keys(username=username)
        if not inactive_keys:
            logger.info(f"rotate_access_key: no inactive access key found for user '{username}'")
            return []

        oldest_inactive_key = inactive_keys[0]
        access_key_id = oldest_inactive_key['AccessKeyId']
        age_days = self.calculate_days(create_date=oldest_inactive_key['CreateDate'])
        try:
            last_used_date = self._iam_operations.get_iam_client.get_access_key_last_used(
                AccessKeyId=access_key_id).get('AccessKeyLastUsed', {}).get('LastUsedDate')
            last_activity_days = self.calculate_days(create_date=last_used_date) if last_used_date else age_days
        except Exception as err:
            logger.error(f"Failed to get last used date for access key '{access_key_id}': {err}")
            last_activity_days = None

        _ROTATED_USERS.add(username)
        credentials = self._iam_operations.rotate_user_access_key(username=username,
                                                                  dry_run=self._dry_run != 'no')
        if credentials:
            self._store_credentials(username, *credentials)

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
