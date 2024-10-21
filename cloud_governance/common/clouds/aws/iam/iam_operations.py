import os

import boto3

from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class IAMOperations:

    def __init__(self, iam_client=None):
        self.iam_client = iam_client if iam_client else get_boto3_client('iam')
        self.utils = Utils()
        self.__sts_client = boto3.client('sts')

    @property
    def get_iam_client(self):
        return self.iam_client

    def get_user_tags(self, username: str):
        """
        This method return tags from the iam resources
        @param username:
        @return:
        """
        try:
            user = self.iam_client.get_user(UserName=username)['User']
            if user.get('Tags'):
                return user.get('Tags')
            else:
                return []
        except:
            return []

    def get_roles(self):
        """
        This method returns all roles
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.iam_client.list_roles, input_tag='Roles',
                                                    check_tag='Marker')

    def get_users(self):
        """
        This method returns all users
        @return:
        """
        return self.utils.get_details_resource_list(self.iam_client.list_users, input_tag='Users', check_tag='Marker')

    def get_account_alias_cloud_name(self):
        """
        This method returns the aws account alias and cloud name
        @return:
        """
        try:
            account_alias = self.iam_client.list_account_aliases()['AccountAliases']
            if account_alias:
                return account_alias[0].upper(), 'AwsCloud'.upper()
        except:
            return os.environ.get('account', '').upper(), 'AwsCloud'.upper()

    def get_iam_users_list(self):
        """
        This method return the IAM users list
        :return:
        """
        iam_users = []
        users = self.get_users()
        for user in users:
            iam_users.append(user.get('UserName'))
        return iam_users

    def get_aws_account_id_name(self):
        """
        This method returns the aws account_id
        :return:
        """
        response = self.__sts_client.get_caller_identity()
        account_id = response['Account']
        return account_id

    def get_role(self, role_name: str):
        """
        This method returns the iam role data
        :param role_name:
        :return:
        """
        role_data = {}
        try:
            role_data = self.iam_client.get_role(RoleName=role_name).get('Role')
        except Exception as err:
            logger.error(err)
        return role_data

    def list_inline_role_policies(self, role_name: str):
        """
        This method returns the iam role inline policies
        :param role_name:
        :return:
        """
        role_policies = []
        try:
            role_policies = self.iam_client.list_role_policies(RoleName=role_name).get('PolicyNames', [])
        except Exception as err:
            logger.error(err)
        return role_policies

    def list_attached_role_policies(self, role_name: str):
        """
        This method returns the iam role attached policies
        :param role_name:
        :return:
        """
        attached_policies = []
        try:
            attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name).get('AttachedPolicies',
                                                                                                    [])
        except Exception as err:
            logger.error(err)
        return attached_policies

    def delete_role(self, role_name: str):
        """
        This method deletes the iam role
        :param role_name:
        :return:
        """
        try:
            self.iam_client.delete_role(RoleName=role_name)
            return True
        except Exception as err:
            raise err

    def tag_role(self, role_name: str, tags: list):
        """
        This method tags the iam role
        :param role_name:
        :param tags:
        :return:
        """
        try:
            self.iam_client.tag_role(RoleName=role_name, Tags=tags)
            return True
        except Exception as err:
            raise err

    def untag_role(self, role_name: str, tags: list):
        """
        This method untags the iam role
        :param role_name:
        :param tags:
        :return:
        """
        try:
            self.iam_client.untag_role(RoleName=role_name,
                                       TagKeys=[key for tag in tags for key, _ in tag.items() if key == 'Key'])
            return True
        except Exception as err:
            raise err
