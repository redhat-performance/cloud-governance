
# TEST DRY RUN: delete=False
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


# zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False, region='us-east-2')


# def test_all_clusters():
#     assert len(zombie_cluster_resources.all_cluster_instance()) >= 0
#
#
# def test_cluster_instance():
#     """
#     This method return all cluster instances, its a private method
#     :return:
#     """
#     assert len(zombie_cluster_resources._cluster_instance()) >= 0
#
#
# def test_zombie_cluster_volume():
#     """
#     This method return all cluster volumes
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_volume()[0]) >= 0
#
#
# def test_zombie_cluster_ami():
#     """
#     This method return all cluster ami
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_ami()[0]) >= 0
#
#
# def test_cluster_snapshot():
#     """
#     This method return all cluster snapshot
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_snapshot()[0]) >= 0
#
#
# def test_zombie_cluster_security_group():
#     """
#     This method return all cluster security_group
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_security_group()[0]) >= 0
#
#
# def test_zombie_cluster_elastic_ip():
#     """
#     This method return all cluster elastic_ip
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_elastic_ip()[0]) >= 0
#
#
# def test_zombie_cluster_network_interface():
#     """
#     This method return all cluster network_interface
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_network_interface()[0]) >= 0
#
#
# def test_zombie_cluster_load_balancer():
#     """
#     This method return all zombie cluster load_balancer
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_load_balancer()[0]) >= 0
#
#
# def test_zombie_cluster_load_balancer_v2():
#     """
#     This method return all cluster load_balancer
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_load_balancer_v2()[0]) >= 0
#
#
# def test_zombie_cluster_cluster_vpc():
#     """
#     This method return all cluster cluster_vpc
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_vpc()[0]) >= 0
#
#
# def test_zombie_cluster_subnet():
#     """
#     This method return all cluster cluster_subnet
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_subnet()[0]) >= 0
#
#
# def test_zombie_cluster_route_table():
#     """
#     This method return all cluster route_table
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_route_table()[0]) >= 0
#
#
# def test_zombie_cluster_internet_gateway():
#     """
#     This method return all cluster internet_gateway
#     :return:
#     """
#     assert  len(zombie_cluster_resources.zombie_cluster_internet_gateway()[0]) >= 0
#
#
# def test_zombie_cluster_dhcp_option():
#     """
#     This method return all cluster dhcp_option
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_dhcp_option()[0]) >= 0
#
#
# def test_zombie_cluster_vpc_endpoint():
#     """
#     This method return all cluster vpc_endpoint
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_vpc_endpoint()[0]) >= 0
#
#
# def test_zombie_cluster_nat_gateway():
#     """
#     This method return all cluster nat_gateway
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_nat_gateway()[0]) >= 0
#
#
# def test_zombie_cluster_network_acl():
#     """
#     This method return zombie network_acl, cross between vpc id in network acl and existing vpcs
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_network_acl()[0]) >= 0
#
#
# def test_zombie_cluster_role():
#     """
#     This method return all zombie cluster role, scan cluster in all regions
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_role()[0]) >= 0
#
#
# def test_zombie_cluster_user():
#     """
#     This method return all zombie cluster user, scan cluster in all regions
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_user()[0]) >= 0
#
#
# def test_zombie_cluster_s3_bucket():
#     """
#     This method return all cluster s3 bucket, scan cluster in all regions
#     :return:
#     """
#     assert len(zombie_cluster_resources.zombie_cluster_s3_bucket()[0]) >= 0
