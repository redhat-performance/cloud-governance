from cloud_governance.common.logger.init_logger import logger


class DeleteIAMResources:
    """
    This class deleted the IAM resources
    IAM Role
    IAM User
    """

    def __init__(self, iam_client):
        self.iam_client = iam_client

    def delete_iam_zombie_resource(self, resource_id: str, resource_type: str):
        if resource_type == 'iam_role':
            self.__delete_iam_role(resource_id)
        elif resource_type == 'iam_user':
            self.__delete_user(resource_id)

    def __delete_iam_role(self, resource_id: str):
        try:
            # Detach policy from role
            self.iam_client.detach_role_policy(RoleName=resource_id, PolicyName=resource_id.replace('role', 'policy'))
            self.iam_client.remove_role_from_instance_profile(RoleName=resource_id,
                                                             InstanceProfileName=resource_id.replace('role',
                                                                                                      'profile'))
            self.iam_client.delete_role(RoleName=resource_id)
            logger.info(f'delete_role: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_role: {resource_id}, {err}')

    def __delete_user(self, resource_id: str):
        try:
            # Detach policy from user
            user_policies = self.iam_client.list_user_policies(UserName=resource_id)
            if user_policies['PolicyNames']:
                self.iam_client.delete_user_policy(UserName=resource_id, PolicyName=f'{resource_id}-policy')
            list_access_key = self.iam_client.list_access_keys(UserName=resource_id)
            # delete user access key
            for access_key in list_access_key['AccessKeyMetadata']:
                self.iam_client.delete_access_key(UserName=resource_id, AccessKeyId=access_key['AccessKeyId'])
            self.iam_client.delete_user(UserName=resource_id)
            logger.info(f'delete_user: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_user: {resource_id}, {err}')