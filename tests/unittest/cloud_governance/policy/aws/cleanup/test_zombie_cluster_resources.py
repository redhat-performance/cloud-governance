from moto import mock_ec2, mock_elb, mock_elbv2, mock_efs

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.zombie_cluster_resource import ZombieClusterResource
from tests.unittest.configs import CLUSTER_TAG1, AWS_DEFAULT_REGION
from tests.unittest.mocks.aws.ec2_create import create_volume, create_vpc, create_subnet, create_network_interface, \
    create_security_group, create_nat_gateway

environment_variables.environment_variables_dict["AWS_DEFAULT_REGION"] = AWS_DEFAULT_REGION


@mock_ec2
def test_zombie_cluster_volume():
    """
    This method tests zombie_cluster_volume returning the volumes
    :return:
    """
    create_volume(cluster_tag=CLUSTER_TAG1)
    zombie_cluster_resource = ZombieClusterResource()
    response = zombie_cluster_resource.zombie_cluster_volume()
    assert CLUSTER_TAG1 in response.keys()
    assert not response[CLUSTER_TAG1]['CleanUpResult']


@mock_ec2
def test_delete_zombie_cluster_volume():
    """
    This method tests deleting zombie_cluster_volume
    :return:
    """
    environment_variables.environment_variables_dict["dry_run"] = "no"
    environment_variables.DAYS_TO_TAKE_ACTION = 1
    create_volume(cluster_tag=CLUSTER_TAG1)
    zombie_cluster_resource = ZombieClusterResource()
    response = zombie_cluster_resource.zombie_cluster_volume()
    assert CLUSTER_TAG1 in response.keys()
    assert response[CLUSTER_TAG1]['CleanUpResult']


@mock_elb
@mock_elbv2
@mock_efs
@mock_ec2
def test_zombie_network_interface():
    """
    This method tests deletion of zombie_network_interface returning the interfaces
    :return:
    """
    environment_variables.environment_variables_dict["dry_run"] = "no"
    environment_variables.ZOMBIE_CLUSTER_RESOURCE_NAME = "zombie_cluster_network_interface"
    environment_variables.DAYS_TO_TAKE_ACTION = 1
    vpc_id1 = create_vpc(CLUSTER_TAG1)['VpcId']
    subnet_id = create_subnet(vpc_id1, CLUSTER_TAG1)['SubnetId']
    create_nat_gateway(subnet_id, CLUSTER_TAG1)
    create_network_interface(subnet_id=subnet_id, cluster_tag=CLUSTER_TAG1)
    zombie_cluster_resource = ZombieClusterResource()
    response = zombie_cluster_resource.run_zombie_cluster_pruner()
    assert CLUSTER_TAG1 in response.keys()
    assert 'zombie_cluster_nat_gateway' in response[CLUSTER_TAG1]['ResourceNames']
    assert response[CLUSTER_TAG1]['CleanUpResult']
    assert len(zombie_cluster_resource._ec2_operations.get_network_interface()) == 0
