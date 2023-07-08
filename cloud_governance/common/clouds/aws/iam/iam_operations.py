import os

import boto3

from cloud_governance.common.clouds.aws.utils.utils import Utils


class IAMOperations:

    def __init__(self, iam_client=None):
        self.iam_client = iam_client if iam_client else boto3.client('iam')
        self.utils = Utils()
        self.__sts_client = sts_client = boto3.client('sts')

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
        return self.utils.get_details_resource_list(func_name=self.iam_client.list_roles, input_tag='Roles', check_tag='Marker')

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
