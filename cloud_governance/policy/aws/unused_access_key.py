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
            for access_key_label, access_key_data in user_data.items():
                if 'access key' in access_key_label.lower():
                    last_activity_days = access_key_data['last_activity_days']
                    age_days = access_key_data['age_days']
                    region = user_data['region']
                    user_name = username
                    tags = user_data.get('Tags', [])
                    cleanup_result = False
                    cleanup_days = 0
                    if last_activity_days and int(last_activity_days) >= UNUSED_ACCESS_KEY_DAYS and self._has_active_access_keys(user_name, access_key_label) and self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                        cleanup_days = self.get_clean_up_days_count(tags=tags)
                        cleanup_result = self.verify_and_delete_resource(resource_id=user_name, tags=tags,
                                                                         clean_up_days=cleanup_days, access_key_label=access_key_label)
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
                                                            resource_state='Active',
                                                            age_days=age_days,
                                                            last_activity_days=last_activity_days,
                                                            unit_price=0)
                        unused_access_keys.append(resource_data)
                    if not cleanup_result:
                        self.update_resource_day_count_tag(resource_id=user_name, cleanup_days=cleanup_days, tags=tags)

        return unused_access_keys
