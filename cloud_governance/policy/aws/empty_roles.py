from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EmptyRoles(NonClusterZombiePolicy):
    """
    This class sends an alert mail for empty role to the user after 4 days and delete after 7 days.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method returns all empty roles, delete if dry_run no
        @return:
        """
        return self.__delete_empty_roles()

    def __delete_empty_roles(self):
        """
        This method deletes the role after 7 days of empty
        @return:
        """
        zombie_roles = []
        roles = self._iam_operations.get_roles()
        for role in roles:
            role_name = role.get('RoleName')
            try:
                get_role = self._iam_client.get_role(RoleName=role.get('RoleName'))['Role']
                tags = get_role.get('Tags')
                if not self._check_cluster_tag(tags=tags):
                    role_empty = False
                    role_attached_policies = self._iam_client.list_attached_role_policies(RoleName=role_name)
                    role_inline_policies = self._iam_client.list_role_policies(RoleName=role_name)
                    if not role_inline_policies.get('PolicyNames') and not role_attached_policies.get('AttachedPolicies'):
                        role_empty = True
                        if not self._get_tag_name_from_tags(tags=tags, tag_name='Name'):
                            tags.append({'Key': 'Name', 'Value': role_name})
                        empty_days = self._get_resource_last_used_days(tags=tags)
                        empty_role = self._check_resource_and_delete(resource_name='IAM Role', resource_id='RoleName', resource_type='CreateRole', resource=get_role, empty_days=empty_days, days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE, tags=tags)
                        if empty_role:
                            zombie_roles.append({
                                'ResourceId': empty_role.get('RoleName'),
                                'Name': empty_role.get('RoleName'),
                                'User': self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                                'Skip': self._get_policy_value(tags=tags),
                                'Days': empty_days})
                    else:
                        empty_days = 0
                    self._update_resource_tags(resource_id=role_name, tags=tags, left_out_days=empty_days, resource_left_out=role_empty)
            except Exception as err:
                logger.info(f'Error occur:{role_name}, {err}')
        return zombie_roles
