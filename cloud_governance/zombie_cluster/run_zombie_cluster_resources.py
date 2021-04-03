from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


def zombie_cluster_resource(delete: bool = False, region: str = 'us-east-2'):
    """
    This method return zombie cluster resources,
    How its works? if not exist an instance cluster, the resource is zombie
    if delete true it will delete the zombie resource
    :return: list of zombie resources
    """
    zombie_result = {}
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=delete, region=region)
    scan_func_resource_list = [zombie_cluster_resources.zombie_cluster_volume,
                          zombie_cluster_resources.zombie_cluster_ami,
                          zombie_cluster_resources.zombie_cluster_snapshot,
                          zombie_cluster_resources.zombie_cluster_security_group,
                          zombie_cluster_resources.zombie_cluster_elastic_ip,
                          zombie_cluster_resources.zombie_cluster_network_interface,
                          zombie_cluster_resources.zombie_cluster_load_balancer,
                          zombie_cluster_resources.zombie_cluster_load_balancer_v2,
                          zombie_cluster_resources.zombie_cluster_vpc,
                          zombie_cluster_resources.zombie_cluster_subnet,
                          zombie_cluster_resources.zombie_cluster_route_table,
                          zombie_cluster_resources.zombie_cluster_internet_gateway,
                          zombie_cluster_resources.zombie_cluster_dhcp_option,
                          zombie_cluster_resources.zombie_cluster_vpc_endpoint,
                          zombie_cluster_resources.zombie_cluster_nat_gateway,
                          zombie_cluster_resources.zombie_network_acl,
                          zombie_cluster_resources.zombie_cluster_role,
                          zombie_cluster_resources.zombie_cluster_user,
                          zombie_cluster_resources.zombie_cluster_s3_bucket]

    delete_func_resource_list = [zombie_cluster_resources.zombie_cluster_volume,
                          zombie_cluster_resources.zombie_cluster_ami,
                          zombie_cluster_resources.zombie_cluster_snapshot,
                          #zombie_cluster_resources.zombie_cluster_security_group,
                          zombie_cluster_resources.zombie_cluster_elastic_ip,
                          zombie_cluster_resources.zombie_cluster_network_interface,
                          zombie_cluster_resources.zombie_cluster_load_balancer,
                          zombie_cluster_resources.zombie_cluster_load_balancer_v2,
                          #zombie_cluster_resources.zombie_cluster_vpc,
                          zombie_cluster_resources.zombie_cluster_subnet,
                          #zombie_cluster_resources.zombie_cluster_route_table,
                          #zombie_cluster_resources.zombie_cluster_internet_gateway,
                          #zombie_cluster_resources.zombie_cluster_dhcp_option,
                          zombie_cluster_resources.zombie_cluster_vpc_endpoint,
                          zombie_cluster_resources.zombie_cluster_nat_gateway,
                          zombie_cluster_resources.zombie_network_acl,
                          zombie_cluster_resources.zombie_cluster_role,
                          zombie_cluster_resources.zombie_cluster_user,
                          zombie_cluster_resources.zombie_cluster_s3_bucket]
    if delete:
        action = 'Delete'
        func_resource_list = delete_func_resource_list
        logger.info("Skip Deleting the following resource due to Dependencies:\n zombie_cluster_security_group, zombie_cluster_vpc, zombie_cluster_route_table, zombie_cluster_internet_gateway, zombie_cluster_dhcp_option")
    else:
        action = 'Scan'
        func_resource_list = scan_func_resource_list
    logger.info(f'{action} {len(func_resource_list)} cluster zombies resources in region {region}:')
    for func in func_resource_list:
        logger.info(f'key: {func.__name__}, count: {len(func())}, data: {func()}')
        zombie_result[func.__name__] = {'count': len(func()), 'data': func()}
    return zombie_result

