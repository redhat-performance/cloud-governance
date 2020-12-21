from cloud_governance.tag_cluster.tag_cluster_resouces import TagClusterResources
from time import gmtime, strftime


cluster_prefix = 'kubernetes.io/cluster/'
cluster_name = 'ocs-test-jlhpd'
#cluster_name = 'opc464-k7jml'

# input tags
mandatory_tags = {
  "Name": "test-opc464",
  "Owner": "Eli Battat",
  "Email": "ebattat@redhat.com",
  "Purpose": "test",
  "Date": strftime("%Y/%m/%d %H:%M:%S")
}
#print(strftime("%Y/%m/%d %H:%M:%S", gmtime()))

tag_cluster_resources = TagClusterResources(cluster_prefix=cluster_prefix, cluster_name=cluster_name, input_tags=mandatory_tags)


def test_init_cluster_name():
    """
    This method search for full cluster key stamp according to part of cluster name
    :return:
    """
    print(tag_cluster_resources.init_cluster_name())


def test_cluster_instance():
    """
    This method return all cluster instances
    :return:
    """
    print(tag_cluster_resources.cluster_instance())


def test_cluster_volume():
    """
    This method return all cluster volumes
    :return:
    """
    print(tag_cluster_resources.cluster_volume())


def test_cluster_ami():
    """
    This method return all cluster ami
    :return:
    """
    print(tag_cluster_resources.cluster_ami())


def test_cluster_snapshot():
    """
    This method return all cluster snapshot
    :return:
    """
    print(tag_cluster_resources.cluster_snapshot())


def test_cluster_security_group():
    """
    This method return all cluster security_group
    :return:
    """
    print(tag_cluster_resources.cluster_security_group())


def test_cluster_elastic_ip():
    """
    This method return all cluster elastic_ip
    :return:
    """
    print(tag_cluster_resources.cluster_elastic_ip())


def test_cluster_network_interface():
    """
    This method return all cluster network_interface
    :return:
    """
    print(tag_cluster_resources.cluster_network_interface())


def test_cluster_load_balancer():
    """
    This method return all cluster load_balancer
    :return:
    """
    print(tag_cluster_resources.cluster_load_balancer())


def test_cluster_load_balancer_v2():
    """
    This method return all cluster load_balancer
    :return:
    """
    print(tag_cluster_resources.cluster_load_balancer_v2())


def test_cluster_cluster_vpc():
    """
    This method return all cluster cluster_vpc
    :return:
    """
    print(tag_cluster_resources.cluster_vpc())


def test_cluster_cluster_subnet():
    """
    This method return all cluster cluster_subnet
    :return:
    """
    print(tag_cluster_resources.cluster_subnet())


def test_cluster_route_table():
    """
    This method return all cluster route_table
    :return:
    """
    print(tag_cluster_resources.cluster_route_table())


def test_cluster_internet_gateway():
    """
    This method return all cluster internet_gateway
    :return:
    """
    print(tag_cluster_resources.cluster_internet_gateway())


def test_cluster_dhcp_option():
    """
    This method return all cluster dhcp_option
    :return:
    """
    print(tag_cluster_resources.cluster_dhcp_option())


def test_cluster_vpc_endpoint():
    """
    This method return all cluster vpc_endpoint
    :return:
    """
    print(tag_cluster_resources.cluster_vpc_endpoint())


def test_cluster_nat_gateway():
    """
    This method return all cluster nat_gateway
    :return:
    """
    print(tag_cluster_resources.cluster_nat_gateway())


def test_cluster_network_acl():
    """
    This method return all cluster network_acl
    :return:
    """
    print(tag_cluster_resources.cluster_network_acl())


def test_cluster_role():
    """
    This method return all cluster role
    :return:
    """
    print(tag_cluster_resources.cluster_role())


def test_cluster_s3_bucket():
    """
    This method return all cluster s3_bucket
    :return:
    """
    print(tag_cluster_resources.cluster_s3_bucket())

# print(f'All resource that related to cluster name {cluster_name}')
# # EC2
# print(f'cluster instance:')
# print(cluster_resources.cluster_instance())
# print(f'cluster volume:')
# print(cluster_resources.cluster_volume())
# print(f'cluster ami:')
# print(cluster_resources.cluster_ami())
# print(f'cluster snapshots:')
# print(cluster_resources.cluster_snapshot())
# print(f'cluster security group:')
# print(cluster_resources.cluster_security_group())
# print(f'cluster elastic ip:')
# print(cluster_resources.cluster_elastic_ip())
# print(f'cluster network interface:')
# print(cluster_resources.cluster_network_interface())
# print(f'cluster load balancer:')
# print(cluster_resources.cluster_load_balancer())
#
# # VPC
# print('cluster vpc:')
# print(cluster_resources.cluster_vpc())
# print('cluster subnet:')
# print(cluster_resources.cluster_subnet())
# print('cluster route table:')
# print(cluster_resources.cluster_route_table())
# print('cluster internet gateway:')
# print(cluster_resources.cluster_internet_gateway())
# print('cluster dhcp_option:')
# print(cluster_resources.cluster_dhcp_option())
# print('cluster vpc endpoint:')
# print(cluster_resources.cluster_vpc_endpoint())
# print('cluster nat gateway:')
# print(cluster_resources.cluster_nat_gateway())
# print('cluster network_acl:')
# print(cluster_resources.cluster_network_acl())
#
# # IAM
# print('cluster role:')
# print(cluster_resources.cluster_role())
#
# # S3
# print('cluster s3:')
# print(cluster_resources.cluster_s3_bucket())