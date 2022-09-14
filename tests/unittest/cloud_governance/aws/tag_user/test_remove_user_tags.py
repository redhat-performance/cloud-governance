import boto3
from moto import mock_iam

from cloud_governance.aws.tag_user.remove_user_tags import RemoveUserTags


@mock_iam
def test_remove_user_tags():
    """
    This test tests for removing the tags of user
    @return:
    """
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='test-user', Tags=[{'Key': 'Username', 'Value': 'test-user'}])
    iam_client.create_user(UserName='test-user2', Tags=[{'Key': 'Username', 'Value': 'test-use1r'}])
    remove_tags = RemoveUserTags(remove_keys=['Username'])
    assert remove_tags.user_tags_remove() == 2
