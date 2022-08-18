import os
import uuid
from datetime import datetime

import boto3

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.policy.zombie_cluster_resource import ZombieClusterResources


USER_NAME = os.environ.get('USER_NAME', '')
iam_resource = boto3.client('iam')


def test_iam_zombie_user_create_and_delete():
    """
    This method checks weather the zombie users exists or not
    :return:
    """
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False,
                                                      cluster_tag=f'kubernetes.io/cluster/{USER_NAME}',
                                                      resource_name='zombie_cluster_user')
    assert len(zombie_cluster_resources.zombie_cluster_user()) >= 1
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag=f'kubernetes.io/cluster/{USER_NAME}',
                                                      resource_name='zombie_cluster_user')
    zombie_cluster_resources.zombie_cluster_user()
    iam_users = Utils().get_details_resource_list(func_name=iam_resource.list_users, input_tag='Users',
                                                  check_tag='Marker')
    find = False
    for user in iam_users:
        if user['UserName'] == USER_NAME:
            find = True
            break
    assert not find
