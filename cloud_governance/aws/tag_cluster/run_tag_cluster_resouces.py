from cloud_governance.common.logger.init_logger import logger
from cloud_governance.aws.tag_cluster.remove_cluster_tags import RemoveClusterTags
from cloud_governance.aws.tag_cluster.tag_cluster_resouces import TagClusterResources


def tag_cluster_resource(cluster_name: str = '', mandatory_tags: dict = None, region: str = 'us-east-2', tag_operation: str = 'yes', cluster_only: bool = False):
    """
    This method scan for cluster name in all the cluster resources
    :return: list of cluster resources according to cluster name
    """

    if tag_operation == "update":
        action = 'Tag'
        dry_run = 'no'
    else:
        action = 'read'
        dry_run = 'yes'
    tag_cluster_resources = TagClusterResources(cluster_prefix='kubernetes.io/cluster/', cluster_name=cluster_name,
                                                input_tags=mandatory_tags, region=region, dry_run=dry_run, cluster_only=cluster_only)

    func_resource_list = [tag_cluster_resources.cluster_instance,
                          tag_cluster_resources.cluster_volume,
                          tag_cluster_resources.cluster_ami,
                          tag_cluster_resources.cluster_snapshot,
                          tag_cluster_resources.cluster_network_interface,
                          tag_cluster_resources.cluster_load_balancer,
                          tag_cluster_resources.cluster_load_balancer_v2,
                          tag_cluster_resources.cluster_dhcp_option,
                          tag_cluster_resources.cluster_subnet,
                          tag_cluster_resources.cluster_route_table,
                          tag_cluster_resources.cluster_vpc_endpoint,
                          tag_cluster_resources.cluster_nat_gateway,
                          tag_cluster_resources.cluster_internet_gateway,
                          tag_cluster_resources.cluster_security_group,
                          tag_cluster_resources.cluster_elastic_ip,
                          tag_cluster_resources.cluster_vpc,
                          tag_cluster_resources.cluster_role,
                          tag_cluster_resources.cluster_user,
                          tag_cluster_resources.cluster_s3_bucket,
                          ]
    if cluster_only:
        logger.info(f"{action} {len(func_resource_list)} cluster resources for cluster name '{cluster_name}' in region {region}:")
    else:
        logger.info(f"{action} {len(func_resource_list)} cluster resources for cluster name '{cluster_name}' in region {region}:")
        logger.info(f"{action} 4 non-cluster resources in region {region}:")
    if not cluster_name:
        func_resource_list[0]()
        func_resource_list = func_resource_list[1:-3]
    else:
        func_resource_list[0]()
        func_resource_list = func_resource_list[1:]
    for _, func in enumerate(func_resource_list):
        func()


def remove_cluster_resources_tags(region: str, cluster_name: str, input_tags: dict, cluster_only: bool = False):
    """
    This method removes the tags from the AWS resources
    @param cluster_only:
    @param region:
    @param cluster_name:
    @param input_tags:
    @return:
    """
    remove_cluster_tags = RemoveClusterTags(region=region, cluster_name=cluster_name, cluster_prefix='kubernetes.io/cluster/', input_tags=input_tags, cluster_only=cluster_only)
    func_resource_list = [remove_cluster_tags.cluster_instance,
                          remove_cluster_tags.cluster_volume,
                          remove_cluster_tags.cluster_images,
                          remove_cluster_tags.cluster_snapshot,
                          remove_cluster_tags.cluster_load_balancer,
                          remove_cluster_tags.cluster_load_balancer_v2,
                          remove_cluster_tags.cluster_network_interface,
                          remove_cluster_tags.cluster_elastic_ip,
                          remove_cluster_tags.cluster_security_group,
                          remove_cluster_tags.cluster_vpc,
                          remove_cluster_tags.cluster_subnet,
                          remove_cluster_tags.cluster_route_table,
                          remove_cluster_tags.cluster_internet_gateway,
                          remove_cluster_tags.cluster_dhcp_option,
                          remove_cluster_tags.cluster_vpc_endpoint,
                          remove_cluster_tags.cluster_nat_gateway,
                          remove_cluster_tags.cluster_network_acl,
                          remove_cluster_tags.cluster_role,
                          remove_cluster_tags.cluster_user,
                          remove_cluster_tags.cluster_s3_bucket]
    if cluster_name:
        logger.info(f"{len(func_resource_list)} remove tag cluster resources from '{cluster_name}' in region {region}:")
    else:
        logger.info(f"{len(func_resource_list)} remove tag cluster resources  in region {region}:")
    response = func_resource_list[0]()
    for func in func_resource_list[1:]:
        func(instance_tags=response)
    logger.info(response)

