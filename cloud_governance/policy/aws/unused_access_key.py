from cloud_governance.common.utils.configs import UNUSED_ACCESS_KEY_DAYS
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class UnusedAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "DeActivate"

    def run_policy_operations(self):
        """
        For key age >= UNUSED_ACCESS_KEY_DAYS (e.g. 90): apply a grace period (deactivation_grace_days
        = age_days - UNUSED_ACCESS_KEY_DAYS, capped at DAYS_TO_TAKE_ACTION). During grace period
        write to ES with cleanup_days 1..7 so send_aggregated_alerts sends reminder emails. After
        grace period, deactivate the key.
        """
        unused_access_keys = []
        days_to_take_action = int(self._days_to_take_action)
        iam_users_access_keys = self._get_iam_users_access_keys()
        for username, user_data in iam_users_access_keys.items():
            tags = user_data.get('tags', user_data.get('Tags', []))
            region = user_data['region']
            user_name = username

            for access_key_label, access_key_data in user_data.items():
                if 'access key' not in access_key_label.lower():
                    continue
                last_activity_days = access_key_data.get('last_activity_days')
                age_days = access_key_data.get('age_days')
                status = (access_key_data.get('status') or '').lower()
                if age_days is None:
                    continue
                age_days = int(age_days)

                if status == 'inactive':
                    continue

                if not self._has_active_access_keys(user_name, access_key_label):
                    continue
                if self.get_skip_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
                    continue

                if age_days < UNUSED_ACCESS_KEY_DAYS:
                    continue
                deactivation_grace_days = min(age_days - UNUSED_ACCESS_KEY_DAYS, days_to_take_action)
                cleanup_result = self.verify_and_delete_resource(
                    resource_id=user_name,
                    tags=tags,
                    clean_up_days=deactivation_grace_days,
                    access_key_label=access_key_label,
                )
                resource_data = self._get_es_schema(
                    resource_id=user_name,
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    email=self.get_tag_name_from_tags(tags=tags, tag_name='Email'),
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    cleanup_days=deactivation_grace_days,
                    dry_run=self._dry_run,
                    name=user_name,
                    region=region,
                    cleanup_result=str(cleanup_result),
                    resource_action=self.RESOURCE_ACTION,
                    cloud_name=self._cloud_name,
                    resource_type='UnusedAccessKey',
                    resource_state='Active',
                    age_days=age_days,
                    last_activity_days=last_activity_days,
                    unit_price=0,
                )
                unused_access_keys.append(resource_data)

        return unused_access_keys
