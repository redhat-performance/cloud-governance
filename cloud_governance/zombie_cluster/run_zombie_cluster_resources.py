from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


def __get_resource_list(region, delete: bool = False, resource: str = '', cluster_tag: str = ''):
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=delete, region=region, cluster_tag=cluster_tag)
    zombie_cluster_resources_dict = {'zombie_cluster_volume' : zombie_cluster_resources.zombie_cluster_volume,
                              'zombie_cluster_ami' : zombie_cluster_resources.zombie_cluster_ami,
                              'zombie_cluster_snapshot': zombie_cluster_resources.zombie_cluster_snapshot,
                              'zombie_cluster_security_group': zombie_cluster_resources.zombie_cluster_security_group,
                              'zombie_cluster_elastic_ip' : zombie_cluster_resources.zombie_cluster_elastic_ip,
                              'zombie_cluster_network_interface': zombie_cluster_resources.zombie_cluster_network_interface,
                              'zombie_cluster_load_balancer': zombie_cluster_resources.zombie_cluster_load_balancer,
                              'zombie_cluster_load_balancer_v2': zombie_cluster_resources.zombie_cluster_load_balancer_v2,
                              'zombie_cluster_vpc': zombie_cluster_resources.zombie_cluster_vpc,
                              'zombie_cluster_subnet': zombie_cluster_resources.zombie_cluster_subnet,
                              'zombie_cluster_route_table': zombie_cluster_resources.zombie_cluster_route_table,
                              'zombie_cluster_internet_gateway': zombie_cluster_resources.zombie_cluster_internet_gateway,
                              'zombie_cluster_dhcp_option': zombie_cluster_resources.zombie_cluster_dhcp_option,
                              'zombie_cluster_vpc_endpoint': zombie_cluster_resources.zombie_cluster_vpc_endpoint,
                              'zombie_cluster_nat_gateway': zombie_cluster_resources.zombie_cluster_nat_gateway,
                              'zombie_network_acl': zombie_cluster_resources.zombie_network_acl,
                              'zombie_cluster_role': zombie_cluster_resources.zombie_cluster_role,
                              'zombie_cluster_user': zombie_cluster_resources.zombie_cluster_user,
                              'zombie_cluster_s3_bucket': zombie_cluster_resources.zombie_cluster_s3_bucket}
    if resource:
        scan_func_resource_list = [zombie_cluster_resources_dict[resource]]
        delete_func_resource_list = [zombie_cluster_resources_dict[resource]]
    else:
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
        return delete_func_resource_list
    else:
        return scan_func_resource_list


def zombie_cluster_resource(delete: bool = False, region: str = 'us-east-2', resource: str = '', cluster_tag: str = ''):
    """
    This method return zombie cluster resources,
    How its works? if not exist an instance cluster, the resource is zombie
    if delete true it will delete the zombie resource
    :return: list of zombie resources
    """
    zombie_result = {}
    all_cluster_data = []

    if delete:
        action = 'Delete'
        if resource:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag)
        else:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag)
        logger.info("Skip Deleting the following resource due to Dependencies:\n zombie_cluster_security_group, zombie_cluster_vpc, zombie_cluster_route_table, zombie_cluster_internet_gateway, zombie_cluster_dhcp_option")
    else:
        action = 'Scan'
        if resource:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag)
        else:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag)
    logger.info(f'{action} {len(func_resource_list)} cluster zombies resources in region {region}:')
    for func in func_resource_list:
        resource_data, cluster_data = func()
        logger.info(f'key: {func.__name__}, count: {len(resource_data)}, data: {cluster_data}')
        zombie_result[func.__name__] = {'count': len(resource_data), 'data': set(cluster_data)}
        all_cluster_data.extend(cluster_data)
    zombie_result['all_cluster_data'] = {'count': len(set(all_cluster_data)), 'data': set(all_cluster_data)}
    return zombie_result
