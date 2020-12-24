from ocp.tag_cluster.tag_cluster_resouces import TagClusterResources

from time import gmtime, strftime

#cluster_name = 'ocs-test-jlhpd'
cluster_name = 'ocs-test-jlhpd'

# input tags
mandatory_tags = {
  "Name": "test-opc464",
  "Owner": "Eli Battat",
  "Email": "ebattat@redhat.com",
  "Purpose": "test",
  "Date": strftime("%Y/%m/%d %H:%M:%S")
}

tag_cluster_resources = TagClusterResources(cluster_prefix='kubernetes.io/cluster/', cluster_name=cluster_name, input_tags=mandatory_tags)

func_resource_list = [tag_cluster_resources.cluster_instance,
                      tag_cluster_resources.cluster_volume,
                      tag_cluster_resources.cluster_ami,
                      tag_cluster_resources.cluster_ami,
                      tag_cluster_resources.cluster_snapshot,
                      tag_cluster_resources.cluster_security_group,
                      tag_cluster_resources.cluster_elastic_ip,
                      tag_cluster_resources.cluster_network_interface,
                      tag_cluster_resources.cluster_load_balancer,
                      tag_cluster_resources.cluster_load_balancer_v2,
                      tag_cluster_resources.cluster_vpc,
                      tag_cluster_resources.cluster_subnet,
                      tag_cluster_resources.cluster_route_table,
                      tag_cluster_resources.cluster_internet_gateway,
                      tag_cluster_resources.cluster_dhcp_option,
                      tag_cluster_resources.cluster_vpc_endpoint,
                      tag_cluster_resources.cluster_nat_gateway,
                      tag_cluster_resources.cluster_network_acl,
                      tag_cluster_resources.cluster_role,
                      tag_cluster_resources.cluster_s3_bucket,
                      ]


def tag_cluster_resource():
    """
    This method scan for cluster name in all the cluster resources
    :return: list of cluster resources according to cluster name
    """
    print(f'Scan for cluster name in {len(func_resource_list)} AWS resources:')
    for func in func_resource_list:
        print(f'{func.__name__} count: {len(func())}, {func()}')


tag_cluster_resource()