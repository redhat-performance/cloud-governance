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

tag_cluster_resources = TagClusterResources(cluster_prefix=cluster_prefix, cluster_name=cluster_name, input_tags=mandatory_tags, region='us-east-2')


def test_init_cluster_name():
    """
    This method search for full cluster key stamp according to part of cluster name
    :return:
    """
    assert len(tag_cluster_resources._TagClusterResources__init_cluster_name()) >= 0


def test_cluster_instance():
    """
    This method return all cluster instances
    :return:
    """
    assert len(tag_cluster_resources.cluster_instance()) >= 0


def test_cluster_volume():
    """
    This method return all cluster volumes
    :return:
    """
    assert len(tag_cluster_resources.cluster_volume()) >= 0


def test_cluster_ami():
    """
    This method return all cluster ami
    :return:
    """
    assert len(tag_cluster_resources.cluster_ami()) >= 0


def test_cluster_snapshot():
    """
    This method return all cluster snapshot
    :return:
    """
    assert len(tag_cluster_resources.cluster_snapshot()) >= 0


def test_cluster_security_group():
    """
    This method return all cluster security_group
    :return:
    """
    assert len(tag_cluster_resources.cluster_security_group()) >= 0


def test_cluster_elastic_ip():
    """
    This method return all cluster elastic_ip
    :return:
    """
    assert len(tag_cluster_resources.cluster_elastic_ip()) >= 0


def test_cluster_network_interface():
    """
    This method return all cluster network_interface
    :return:
    """
    assert len(tag_cluster_resources.cluster_network_interface()) >= 0


def test_cluster_load_balancer():
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(tag_cluster_resources.cluster_load_balancer()) >= 0


def test_cluster_load_balancer_v2():
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(tag_cluster_resources.cluster_load_balancer_v2()) >= 0


def test_cluster_vpc():
    """
    This method return all cluster cluster_vpc
    :return:
    """
    assert len(tag_cluster_resources.cluster_vpc()) >= 0


def test_cluster_subnet():
    """
    This method return all cluster cluster_subnet
    :return:
    """
    assert len(tag_cluster_resources.cluster_subnet()) >= 0


def test_cluster_route_table():
    """
    This method return all cluster route_table
    :return:
    """
    assert len(tag_cluster_resources.cluster_route_table()) >= 0


def test_cluster_internet_gateway():
    """
    This method return all cluster internet_gateway
    :return:
    """
    assert len(tag_cluster_resources.cluster_internet_gateway()) >= 0


def test_cluster_dhcp_option():
    """
    This method return all cluster dhcp_option
    :return:
    """
    assert len(tag_cluster_resources.cluster_dhcp_option()) >= 0


def test_cluster_vpc_endpoint():
    """
    This method return all cluster vpc_endpoint
    :return:
    """
    assert len(tag_cluster_resources.cluster_vpc_endpoint()) >= 0


def test_cluster_nat_gateway():
    """
    This method return all cluster nat_gateway
    :return:
    """
    assert len(tag_cluster_resources.cluster_nat_gateway()) >= 0


def test_cluster_network_acl():
    """
    This method return all cluster network_acl
    :return:
    """
    assert len(tag_cluster_resources.cluster_network_acl()) >= 0


def test_cluster_role():
    """
    This method return all cluster role
    :return:
    """
    assert len(tag_cluster_resources.cluster_role()) >= 0


def test_cluster_s3_bucket():
    """
    This method return all cluster s3_bucket
    :return:
    """
    assert len(tag_cluster_resources.cluster_s3_bucket()) >= 0
