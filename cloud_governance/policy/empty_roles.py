from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EmptyRoles(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return all empty roles, delete if dry_run no
        @return:
        """
        zombie_roles_data = []
        zombie_roles = {}
        roles = self._iam_operations.get_roles()
        active_clusters = self._zombie_cluster.all_cluster_instance()
        for role in roles:
            try:
                role_attached_policies = self._iam_client.list_attached_role_policies(RoleName=role.get('RoleName'))
                role_inline_policies = self._iam_client.list_role_policies(RoleName=role.get('RoleName'))
                if not role_inline_policies.get('PolicyNames') and not role_attached_policies.get('AttachedPolicies'):
                    get_role = self._iam_client.get_role(RoleName=role.get('RoleName'))['Role']
                    if not self._check_live_cluster_tag(get_role.get('Tags'), active_clusters.values()):
                        zombie_roles_data.append([role.get('RoleName'), self._get_policy_value(tags=get_role.get('Tags'))])
                        zombie_roles[role.get('RoleName')] = get_role.get('Tags')
            except Exception as err:
                logger.info(f'{err} {role.get("RoleName")}')
        if self._dry_run == 'no':
            for zombie_role, tags in zombie_roles.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    try:
                        self._iam_client.delete_role(RoleName=zombie_role)
                        logger.info(f'Role is deleted: {zombie_role}')
                    except Exception as err:
                        logger.info(f'Exception raised: {err}: {zombie_role}')
        return zombie_roles_data
