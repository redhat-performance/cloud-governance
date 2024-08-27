from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class EmptyRoles(AWSPolicyOperations):
    """
    This class sends an alert mail for empty role to the user after 4 days and delete after 7 days.
    """

    RESOURCE_ACTION = 'Delete'
    IAM_GLOBAL_REGION = 'us-east-1'

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns all Empty buckets
        :return:
        :rtype:
        """
        empty_roles = []
        roles = self._iam_operations.get_roles()
        for role in roles:
            role_name = role.get('RoleName')
            role_data = self._iam_operations.get_role(role_name=role_name)
            tags = role_data.get('Tags', [])
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_days = 0
            inline_policies = self._iam_operations.list_inline_role_policies(role_name=role_name)
            attached_policies = self._iam_operations.list_attached_role_policies(role_name=role_name)
            try:
                if not cluster_tag and len(inline_policies) == 0 and len(attached_policies) == 0 and \
                    self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(resource_id=role_name, tags=tags,
                                                                     clean_up_days=cleanup_days)
                    resource_data = self._get_es_schema(resource_id=role_name,
                                                        user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                        skip_policy=self.get_skip_policy_value(tags=tags),
                                                        cleanup_days=cleanup_days,
                                                        dry_run=self._dry_run,
                                                        name=role_name,
                                                        region=self.IAM_GLOBAL_REGION,
                                                        cleanup_result=str(cleanup_result),
                                                        resource_action=self.RESOURCE_ACTION,
                                                        cloud_name=self._cloud_name,
                                                        resource_type='EmptyRole',
                                                        resource_state="Empty",
                                                        unit_price=0)
                    empty_roles.append(resource_data)
                if not cleanup_result:
                    self.update_resource_day_count_tag(resource_id=role_name, cleanup_days=cleanup_days, tags=tags)
            except Exception as e:
                logger.error(f'Exception raised while processing the empty roles operation on {role_name}, {e}')
        return empty_roles
