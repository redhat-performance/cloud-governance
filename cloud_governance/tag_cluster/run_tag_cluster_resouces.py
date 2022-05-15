from cloud_governance.common.logger.init_logger import logger
from cloud_governance.tag_cluster.tag_cluster_resouces import TagClusterResources
from multiprocessing import Process


def tag_cluster_resource(cluster_name: str = '', mandatory_tags: dict = None, region: str = 'us-east-2', dry_run: str = 'yes'):
    """
    This method scan for cluster name in all the cluster resources
    :return: list of cluster resources according to cluster name
    """

    tag_cluster_resources = TagClusterResources(cluster_prefix='kubernetes.io/cluster/', cluster_name=cluster_name,
                                                input_tags=mandatory_tags, region=region, dry_run=dry_run)

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
    if dry_run == "no":
        action = 'Tag'
    else:
        action = 'Scan'
    logger.info(f"{action} {len(func_resource_list)} cluster resources for cluster name '{cluster_name}' in region {region}:")
    if not cluster_name:
        func_resource_list[0]()
        func_resource_list = func_resource_list[1:-3]
    else:
        func_resource_list[0]()
        func_resource_list = func_resource_list[1:]
    jobs = []
    for _, func in enumerate(func_resource_list):
        p = Process(target=func)
        jobs.append(p)
        p.start()
    for job in jobs:
        job.join()
