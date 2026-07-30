import boto3
from moto import mock_aws

from cloud_governance.policy.policy_operations.aws.tag_user.remove_user_tags import RemoveUserTags


@mock_aws
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


@mock_aws
def test_capa_cluster_user_protected_from_tag_removal():
    """
    This test verifies that a user tagged with a CAPA cluster key is identified
    as a cluster service account and protected from governance tag removal.
    @return:
    """
    iam_client = boto3.client('iam')
    capa_cluster_tag = 'sigs.k8s.io/cluster-api-provider-aws/cluster/test-cluster'
    iam_client.create_user(
        UserName='capa-sa-user',
        Tags=[
            {'Key': capa_cluster_tag, 'Value': 'owned'},
            {'Key': 'Username', 'Value': 'capa-sa-user'},
        ]
    )
    remove_tags = RemoveUserTags(remove_keys=['Username'])
    removed_count = remove_tags.user_tags_remove()
    assert removed_count == 0
