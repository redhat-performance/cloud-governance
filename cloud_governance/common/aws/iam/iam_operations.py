import boto3


class IAMOperations:

    def __init__(self):
        self.iam_client = boto3.client('iam')

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
                return ''
        except:
            return ''
