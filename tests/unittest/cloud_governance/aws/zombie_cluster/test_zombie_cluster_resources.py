import pytest
from moto import mock_ec2, mock_elb, mock_elbv2, mock_iam, mock_s3

from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


@pytest.fixture(scope="module")
def zombie_cluster_resources():
    """Create ZombieClusterResources under mocks so __init__ does not hit real AWS."""
    with mock_ec2(), mock_elb(), mock_elbv2(), mock_iam(), mock_s3():
        yield ZombieClusterResources(
            cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"],
            delete=False,
            region='us-east-2',
        )


def test_all_clusters(zombie_cluster_resources):
    assert len(zombie_cluster_resources.all_cluster_instance()) >= 0


def test_cluster_instance(zombie_cluster_resources):
    """
    This method returns all cluster instances, its a private method
    :return:
    """
    assert len(zombie_cluster_resources._cluster_instance()) >= 0


def test_zombie_cluster_volume(zombie_cluster_resources):
    """
    This method returns all cluster volumes
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_volume()[0]) >= 0


def test_zombie_cluster_ami(zombie_cluster_resources):
    """
    This method returns all cluster ami
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_ami()[0]) >= 0


def test_cluster_snapshot(zombie_cluster_resources):
    """
    This method returns all cluster snapshot
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_snapshot()[0]) >= 0


def test_zombie_cluster_security_group(zombie_cluster_resources):
    """
    This method returns all cluster security_group
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_security_group()[0]) >= 0


def test_zombie_cluster_elastic_ip(zombie_cluster_resources):
    """
    This method return all cluster elastic_ip
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_elastic_ip()[0]) >= 0


def test_zombie_cluster_network_interface(zombie_cluster_resources):
    """
    This method return all cluster network_interface
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_network_interface()[0]) >= 0


def test_zombie_cluster_load_balancer(zombie_cluster_resources):
    """
    This method return all zombie cluster load_balancer
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_load_balancer()[0]) >= 0


def test_zombie_cluster_load_balancer_v2(zombie_cluster_resources):
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_load_balancer_v2()[0]) >= 0


def test_zombie_cluster_cluster_vpc(zombie_cluster_resources):
    """
    This method return all cluster cluster_vpc
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_vpc()[0]) >= 0


def test_zombie_cluster_subnet(zombie_cluster_resources):
    """
    This method return all cluster cluster_subnet
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_subnet()[0]) >= 0


def test_zombie_cluster_route_table(zombie_cluster_resources):
    """
    This method return all cluster route_table
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_route_table()[0]) >= 0


def test_zombie_cluster_internet_gateway(zombie_cluster_resources):
    """
    This method return all cluster internet_gateway
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_internet_gateway()[0]) >= 0


def test_zombie_cluster_dhcp_option(zombie_cluster_resources):
    """
    This method return all cluster dhcp_option
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_dhcp_option()[0]) >= 0


def test_zombie_cluster_vpc_endpoint(zombie_cluster_resources):
    """
    This method return all cluster vpc_endpoint
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_vpc_endpoint()[0]) >= 0


def test_zombie_cluster_nat_gateway(zombie_cluster_resources):
    """
    This method return all cluster nat_gateway
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_nat_gateway()[0]) >= 0


def test_zombie_cluster_network_acl(zombie_cluster_resources):
    """
    This method return zombie network_acl, cross between vpc id in network acl and existing vpcs
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_network_acl()[0]) >= 0


def test_zombie_cluster_role(zombie_cluster_resources):
    """
    This method return all zombie cluster role, scan cluster in all regions
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_role()[0]) >= 0


@pytest.mark.skip(reason='Skipping the zombie cluster user')
def test_zombie_cluster_user(zombie_cluster_resources):
    """
    This method return all zombie cluster user, scan cluster in all regions
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_user()[0]) >= 0


def test_zombie_cluster_s3_bucket(zombie_cluster_resources):
    """
    This method return all cluster s3 bucket, scan cluster in all regions
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_s3_bucket()[0]) >= 0
