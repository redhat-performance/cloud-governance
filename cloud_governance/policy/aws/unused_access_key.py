from cloud_governance.common.utils.configs import UNUSED_ACCESS_KEY_DAYS, UNUSED_ACCESS_KEY_MAX_DAY
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class UnusedAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "DeActivate"

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns a list of users with at least one active access key whose last used date is greater than UNUSED_ACCESS_KEY_DAYS
        :return:
        :rtype:
        """
        unused_access_keys = []
        iam_users_access_keys = self._get_iam_users_access_keys()
        for username, user_data in iam_users_access_keys.items():
            last_activity_days = user_data['last_activity_days']
            # Collect age_days only for active access keys
            age_days_list = [
                value[1] for key, value in user_data.items()
                if key.startswith("Access key") and isinstance(value, list) and value[0] == "active"
            ]
            # "N/A"/None implies unused access key — fallback to UNUSED_ACCESS_KEY_MAX_DAY
            age_days = min(age_days_list) if age_days_list else UNUSED_ACCESS_KEY_MAX_DAY
            # if access key last_activity_days is "N/A", use age_days
            if last_activity_days == "N/A":
                last_activity_days = age_days
            region = user_data['region']
            user_name = username
            tags = user_data.get('Tags', [])
            cleanup_result = False
            cleanup_days = 0
            if int(last_activity_days) >= UNUSED_ACCESS_KEY_DAYS and self._has_active_access_keys(user_name) and self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                resource_data = self._get_es_schema(resource_id=user_name,
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days,
                                                    dry_run=self._dry_run,
                                                    name=user_name,
                                                    region=region,
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    resource_type='UnusedAccessKey',
                                                    resource_state='Unused',
                                                    age_days=age_days,
                                                    last_activity_days=last_activity_days,
                                                    unit_price=0)
                unused_access_keys.append(resource_data)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=user_name, cleanup_days=cleanup_days, tags=tags)

        return unused_access_keys
