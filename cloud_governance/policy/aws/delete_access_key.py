"""
Policy to delete inactive IAM access keys older than DELETE_ACCESS_KEY_DAYS.
"""
from cloud_governance.common.utils.configs import DELETE_ACCESS_KEY_DAYS
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class DeleteAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "Delete"

    def run_policy_operations(self):
        """
        For inactive keys with age > DELETE_ACCESS_KEY_DAYS: apply a grace period
        (deletion_grace_days = age_days - DELETE_ACCESS_KEY_DAYS, capped at DAYS_TO_TAKE_ACTION). During
        grace period write to ES with cleanup_days 1..7 so send_aggregated_alerts sends
        reminder emails. After grace period, delete the key.
        """
        result = []
        days_to_take_action = int(self._days_to_take_action)
        iam_users_access_keys = self._get_iam_users_access_keys()

        for username, user_data in iam_users_access_keys.items():
            tags = user_data.get('tags', user_data.get('Tags', []))
            region = user_data['region']
            user_name = username

            for access_key_label, access_key_data in user_data.items():
                if 'access key' not in access_key_label.lower():
                    continue
                age_days = access_key_data.get('age_days')
                status = (access_key_data.get('status') or '').lower()
                if age_days is None or status != 'inactive':
                    continue
                age_days = int(age_days)

                key_num = access_key_label.split()[-1]
                inactive_tag_key = f"UnusedAccessKey{key_num}InactiveDate"
                inactive_date_str = self.get_tag_name_from_tags(tags=tags, tag_name=inactive_tag_key)
                delete_all_inactive = self._environment_variables_dict.get('DELETE_INACTIVE_KEYS_WITHOUT_TAG', False)
                if not (age_days > DELETE_ACCESS_KEY_DAYS and (inactive_date_str or delete_all_inactive)):
                    continue

                deletion_grace_days = min(age_days - DELETE_ACCESS_KEY_DAYS, days_to_take_action)
                cleanup_result = self.verify_and_delete_resource(
                    resource_id=user_name,
                    tags=tags,
                    clean_up_days=deletion_grace_days,
                    access_key_label=access_key_label,
                    access_key_id=access_key_data.get('access_key_id'),
                    remove_inactive_tag=bool(inactive_date_str),
                )
                resource_data = self._get_es_schema(
                    resource_id=user_name,
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    cleanup_days=deletion_grace_days,
                    dry_run=self._dry_run,
                    name=user_name,
                    region=region,
                    cleanup_result=str(cleanup_result),
                    resource_action=self.RESOURCE_ACTION,
                    cloud_name=self._cloud_name,
                    resource_type='UnusedAccessKey',
                    resource_state='Inactive',
                    age_days=age_days,
                    last_activity_days=access_key_data.get('last_activity_days'),
                    unit_price=0,
                )
                result.append(resource_data)

        return result
