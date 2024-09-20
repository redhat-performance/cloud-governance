import typeguard

from cloud_governance.common.logger.init_logger import logger


class DeleteIAMResources:
    """
    This class deleted the IAM resources
    IAM Role
    IAM User
    """

    def __init__(self, iam_client):
        """
        Initialize the aws clients
        :param iam_client:
        """
        self.iam_client = iam_client

    @typeguard.typechecked
    def delete_iam_zombie_resource(self, resource_id: str, resource_type: str):
        """
        This method checks for the which resource to delete
        :param resource_id:
        :param resource_type:
        :return:
        """
        if resource_type == 'iam_role':
            self.__delete_iam_role(resource_id)
        elif resource_type == 'iam_user':
            self.__delete_user(resource_id)

    @typeguard.typechecked
    def __delete_iam_role(self, resource_id: str):
        """
        This method deleted the zombie cluster iam role
        :param resource_id:
        :return:
        """
        try:
            # Detach policy from role
            role_policies = self.iam_client.list_attached_role_policies(RoleName=resource_id)
            if role_policies['AttachedPolicies']:
                for role_policy in role_policies['AttachedPolicies']:
                    self.iam_client.detach_role_policy(RoleName=resource_id, PolicyArn=role_policy.get('PolicyArn'))
                    self.iam_client.delete_policy(PolicyArn=role_policy.get('PolicyArn'))
            policy_names = self.iam_client.list_role_policies(RoleName=resource_id)
            if policy_names.get('PolicyNames'):
                for policy in policy_names.get('PolicyNames'):
                    self.iam_client.delete_role_policy(RoleName=resource_id, PolicyName=policy)
            instance_policies = self.iam_client.list_instance_profiles_for_role(RoleName=resource_id)
            if instance_policies['InstanceProfiles']:
                self.iam_client.remove_role_from_instance_profile(RoleName=resource_id,
                                                                  InstanceProfileName=resource_id.replace('role',
                                                                                                          'profile'))
            self.iam_client.delete_role(RoleName=resource_id)
            logger.info(f'delete_role: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_role: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_user(self, resource_id: str):
        """
        This method deletes the Zombie cluster user
        :param resource_id:
        :return:
        """
        try:
            # Detach policy from user
            user_policies = self.iam_client.list_user_policies(UserName=resource_id)
            try:
                if user_policies['PolicyNames']:
                    self.iam_client.delete_user_policy(UserName=resource_id, PolicyName=f'{resource_id}-policy')
            except Exception:
                logger.exception(f'Cannot delete_policies: {user_policies.get("PolicyNames")}')
            list_access_key = self.iam_client.list_access_keys(UserName=resource_id)
            # @Todo user_delete permission is very problematic operation, it might affect other users.
            # delete user access key
            # for access_key in list_access_key['AccessKeyMetadata']:
            #     self.iam_client.delete_access_key(UserName=resource_id, AccessKeyId=access_key['AccessKeyId'])
            # self.iam_client.delete_user(UserName=resource_id)
            logger.info(f'delete_user: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_user: {resource_id}, {err}')
