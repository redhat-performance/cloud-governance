import boto3

from cloud_governance.common.clouds.aws.utils.utils import Utils


class IAMOperations:

    def __init__(self):
        self.iam_client = boto3.client('iam')
        self.utils = Utils()

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
