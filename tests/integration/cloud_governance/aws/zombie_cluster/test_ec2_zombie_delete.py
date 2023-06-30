from datetime import date

import boto3
import pytest

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


def create_vpc():
    """
    This method creates a test vpc
    :return:
    """
    ec2_client = boto3.client('ec2', region_name='us-east-2')
    tags = [
        {'Key': 'kubernetes.io/cluster/integration-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'integration'},
        {'Key': 'Time', 'Value': str(date.today())}
    ]
    ec2_client.create_vpc(CidrBlock='10.0.0.0/16', TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}])


@pytest.mark.skip(reason='Read Only')
def test_ec2_zombie_vpc_exists():
    """
    This method verify zombie cluster not deleted
    :return:
    """
    create_vpc()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      region='us-east-2',
                                                      resource_name='zombie_cluster_vpc')
    assert len(zombie_cluster_resources.zombie_cluster_vpc()[0]) >= 1


@pytest.mark.skip(reason='Read Only')
def test_ec2_zombie_vpc_delete():
    """
    This method tests the zombie vpc delete
    :return:
    """
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      region='us-east-2',
                                                      resource_name='zombie_cluster_vpc', force_delete=True)
    zombie_cluster_resources.zombie_cluster_vpc()
    assert not EC2Operations().find_vpc('kubernetes.io/cluster/integration-test-cluster')

