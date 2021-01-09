from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False, region='us-east-2')


def test_cluster_instance():
    """
    This method return all cluster instances, its a private method
    :return:
    """
    assert len(zombie_cluster_resources._cluster_instance()) >= 0


def test_zombie_cluster_volume():
    """
    This method return all cluster volumes
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_volume()) >= 0


def test_zombie_cluster_ami():
    """
    This method return all cluster ami
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_ami()) >= 0


def test_cluster_snapshot():
    """
    This method return all cluster snapshot
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_snapshot()) >= 0


def test_zombie_cluster_security_group():
    """
    This method return all cluster security_group
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_security_group())


def test_zombie_cluster_elastic_ip():
    """
    This method return all cluster elastic_ip
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_elastic_ip())


def test_zombie_cluster_network_interface():
    """
    This method return all cluster network_interface
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_network_interface()) >= 0


def test_zombie_cluster_load_balancer():
    """
    This method return all zombie cluster load_balancer
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_load_balancer()) >= 0


def test_zombie_cluster_load_balancer_v2():
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_load_balancer_v2()) >= 0


def test_zombie_cluster_cluster_vpc():
    """
    This method return all cluster cluster_vpc
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_vpc())


def test_zombie_cluster_subnet():
    """
    This method return all cluster cluster_subnet
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_subnet()) >= 0


def test_zombie_cluster_route_table():
    """
    This method return all cluster route_table
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_route_table())


def test_zombie_cluster_internet_gateway():
    """
    This method return all cluster internet_gateway
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_internet_gateway())


def test_zombie_cluster_dhcp_option():
    """
    This method return all cluster dhcp_option
    :return:
    """
    print(zombie_cluster_resources.zombie_cluster_dhcp_option())


def test_zombie_cluster_vpc_endpoint():
    """
    This method return all cluster vpc_endpoint
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_vpc_endpoint())


def test_zombie_cluster_nat_gateway():
    """
    This method return all cluster nat_gateway
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_nat_gateway()) >= 0


def test_zombie_network_acl():
    """
    This method return zombie network_acl, cross between vpc id in network acl and existing vpcs
    :return:
    """
    assert len(zombie_cluster_resources.zombie_network_acl()) >= 0


def test_zombie_cluster_role():
    """
    This method return all cluster role
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_role()) >= 0


def test_zombie_cluster_s3_bucket():
    """
    This method return all cluster s3_bucket
    :return:
    """
    assert len(zombie_cluster_resources.zombie_cluster_s3_bucket())  >= 0
