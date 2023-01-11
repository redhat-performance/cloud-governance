import uuid
from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


def test_iam_zombie_user_create_and_delete():
    """
    This method checks weather the zombie users exists or not
    :return:
    """
    short_random_id = uuid.uuid1()
    time_ms = str(datetime.utcnow().strftime('%f'))
    USER_NAME = f'integration-ocp-{short_random_id}-{time_ms}'
    iam_resource = boto3.client('iam')
    tags = [
        {'Key': f'kubernetes.io/cluster/{USER_NAME}', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'integration'}
    ]
    try:
        iam_resource.create_user(UserName=USER_NAME, Tags=tags)
        zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False,
                                                          cluster_tag=f'kubernetes.io/cluster/{USER_NAME}',
                                                          resource_name='zombie_cluster_user', force_delete=True)
        assert len(zombie_cluster_resources.zombie_cluster_user()) >= 1
        zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                          cluster_tag=f'kubernetes.io/cluster/{USER_NAME}',
                                                          resource_name='zombie_cluster_user', force_delete=True)
        zombie_cluster_resources.zombie_cluster_user()
        iam_users = Utils().get_details_resource_list(func_name=iam_resource.list_users, input_tag='Users',
                                                      check_tag='Marker')
        find = False
        for user in iam_users:
            if user['UserName'] == USER_NAME:
                find = True
                break
        assert not find
    except Exception as err:
        iam_users = Utils().get_details_resource_list(func_name=iam_resource.list_users, input_tag='Users', check_tag='Marker')
        for user in iam_users:
            if user['UserName'] == USER_NAME:
                iam_resource.delete_user(UserName=USER_NAME)
        raise Exception('Failed to delete User')
