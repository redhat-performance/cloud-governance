import boto3

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class RemoveUserTags:
    """
    This class contain methods of removing user tags
    """

    def __init__(self, remove_keys: list, username: str = ''):
        self.remove_keys = remove_keys
        self.username = username
        self.iam_client = boto3.client('iam')
        self.IAMOperations = IAMOperations()
        self.get_detail_resource_list = Utils().get_details_resource_list

    def __cluster_user(self, tags: list):
        """
        This method check the user is cluster or not
        @param tags:
        @return:
        """
        for tag in tags:
            if 'kubernetes.io/cluster' in tag.get('Key'):
                return True
        return False

    def user_tags_remove(self):
        """
        This method check the user
        @return:
        """
        users = self.get_detail_resource_list(func_name=self.iam_client.list_users, input_tag='Users',
                                              check_tag='Marker')
        count = 0
        for user in users:
            user_name = user.get('UserName')
            if self.username:
                if self.username == user_name:
                    self.iam_client.untag_user(UserName=user_name, TagKeys=self.remove_keys)
                    count += 1
                    logger.info(f'Username :: {user_name} :: {self.remove_keys}')
                    break
            else:
                user_tags = self.IAMOperations.get_user_tags(username=user_name)
                if not self.__cluster_user(tags=user_tags):
                    self.iam_client.untag_user(UserName=user_name, TagKeys=self.remove_keys)
                    count += 1
                    logger.info(f'Username :: {user_name} :: {self.remove_keys}')
        return count
