import uuid
import boto3

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


short_random_id = uuid.uuid1()
USER_NAME = f'integration-ocp-user-{short_random_id}'

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
    iam_resource.create_user(UserName=USER_NAME, Tags=tags)


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
        if role['UserName'] == USER_NAME:
            find = True
            break
    assert not find



