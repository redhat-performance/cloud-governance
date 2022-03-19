from moto import mock_iam, mock_ec2
import boto3

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


def create_user():
    """
    This method creates a s3 bucket for test
    :return:
    """
    iam_resource = boto3.client('iam')
    tags = [
        {'Key': 'kubernetes.io/cluster/integration-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'integration'}
    ]
    iam_resource.create_user(UserName='integration-ocp-user', Tags=tags)


def test_iam_zombie_user():
    """
    This method checks weather the zombie users exists or not
    :return:
    """
    create_user()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      resource_name='zombie_cluster_user')
    assert len(zombie_cluster_resources.zombie_cluster_user()) >= 1


#'An error occurred (AccessDenied) when calling the ListUserPolicies operation: User: arn:aws:iam::452958939641:user/cloud-governance-user is not authorized to perform: iam:ListUserPolicies on resource: user integration-ocp-user'
def test_delete_iam_cluster_user():
    """
    This method tests the user has successfully deleted or not
    :return:
    """
    iam_resource = boto3.client('iam')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      resource_name='zombie_cluster_user')
    zombie_cluster_resources.zombie_cluster_user()
    iam_users = Utils().get_details_resource_list(func_name=iam_resource.list_users, input_tag='Users', check_tag='Marker')
    find = False
    for role in iam_users:
        if role['UserName'] == 'integration-ocp-user':
            find = True
            break
    assert not find



