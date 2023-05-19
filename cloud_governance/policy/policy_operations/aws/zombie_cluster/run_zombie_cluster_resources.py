
import typeguard

from cloud_governance.policy.policy_operations.aws.zombie_cluster.zombie_cluster_common_methods import ZombieClusterCommonMethods
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


@typeguard.typechecked
def __get_resource_list(region, delete: bool = False, resource: str = '', cluster_tag: str = '',
                        resource_name: str = '', service_type: str = ' '):
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=delete,
                                                      region=region, cluster_tag=cluster_tag,
                                                      resource_name=resource_name)
    zombie_cluster_resources_dict = {'zombie_cluster_volume': zombie_cluster_resources.zombie_cluster_volume,
                                     'zombie_cluster_ami': zombie_cluster_resources.zombie_cluster_ami,
                                     'zombie_cluster_snapshot': zombie_cluster_resources.zombie_cluster_snapshot,
                                     'zombie_cluster_security_group': zombie_cluster_resources.zombie_cluster_security_group,
                                     'zombie_cluster_elastic_ip': zombie_cluster_resources.zombie_cluster_elastic_ip,
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
                                     'zombie_cluster_network_acl': zombie_cluster_resources.zombie_cluster_network_acl,
                                     'zombie_cluster_role': zombie_cluster_resources.zombie_cluster_role,
                                     'zombie_cluster_user': zombie_cluster_resources.zombie_cluster_user,
                                     'zombie_cluster_s3_bucket': zombie_cluster_resources.zombie_cluster_s3_bucket}
    ec2_zombie_resource_services = [zombie_cluster_resources.zombie_cluster_ami,
                                    zombie_cluster_resources.zombie_cluster_volume,
                                    zombie_cluster_resources.zombie_cluster_load_balancer,
                                    zombie_cluster_resources.zombie_cluster_load_balancer_v2,
                                    zombie_cluster_resources.zombie_cluster_snapshot,
                                    zombie_cluster_resources.zombie_cluster_vpc_endpoint,
                                    zombie_cluster_resources.zombie_cluster_dhcp_option,
                                    zombie_cluster_resources.zombie_cluster_route_table,
                                    zombie_cluster_resources.zombie_cluster_security_group,
                                    zombie_cluster_resources.zombie_cluster_nat_gateway,
                                    zombie_cluster_resources.zombie_cluster_network_acl,
                                    zombie_cluster_resources.zombie_cluster_network_interface,
                                    zombie_cluster_resources.zombie_cluster_elastic_ip,
                                    zombie_cluster_resources.zombie_cluster_internet_gateway,
                                    zombie_cluster_resources.zombie_cluster_subnet,
                                    zombie_cluster_resources.zombie_cluster_vpc
                                    ]
    iam_zombie_resource_services = [zombie_cluster_resources.zombie_cluster_role,
                                    zombie_cluster_resources.zombie_cluster_user]
    s3_zombie_resource_services = [zombie_cluster_resources.zombie_cluster_s3_bucket]
    scan_func_resource_list = []
    delete_func_resource_list = []
    if resource:
        scan_func_resource_list = [zombie_cluster_resources_dict[resource]]
        delete_func_resource_list = [zombie_cluster_resources_dict[resource]]
    else:
        if service_type:
            if service_type == 'ec2_zombie_resource_service':
                scan_func_resource_list.extend(ec2_zombie_resource_services)
                delete_func_resource_list.extend(ec2_zombie_resource_services)
            elif service_type == 'iam_zombie_resource_service':
                scan_func_resource_list.extend(iam_zombie_resource_services)
                delete_func_resource_list.extend(iam_zombie_resource_services)
            elif service_type == 's3_zombie_resource_service':
                scan_func_resource_list.extend(s3_zombie_resource_services)
                delete_func_resource_list.extend(s3_zombie_resource_services)
        else:
            scan_func_resource_list = ec2_zombie_resource_services + iam_zombie_resource_services + s3_zombie_resource_services
            delete_func_resource_list = ec2_zombie_resource_services + iam_zombie_resource_services + s3_zombie_resource_services
    if delete:
        return delete_func_resource_list
    else:
        return scan_func_resource_list


@typeguard.typechecked
@logger_time_stamp
def zombie_cluster_resource(delete: bool = False, region: str = 'us-east-2', resource: str = '', cluster_tag: str = '',
                            resource_name: str = '', service_type: str = ''):
    """
    This method returns zombie cluster resources,
    How its works? if not exist an instance cluster, the resource is zombie
    if delete true it will delete the zombie resource
    :return: list of zombie resources
    """
    zombie_result = {}
    all_cluster_data = []

    if delete:
        action = 'Delete'
        if resource:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag, resource_name, service_type)
        else:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag, resource_name, service_type)
        logger.info(
            "Skip Deleting the following resource due to Dependencies:\n zombie_cluster_security_group, zombie_cluster_vpc, zombie_cluster_route_table, zombie_cluster_internet_gateway, zombie_cluster_dhcp_option")
    else:
        action = 'Scan'
        if resource:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag, resource_name, service_type)
        elif resource_name:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag, resource_name, service_type)
        else:
            func_resource_list = __get_resource_list(region, delete, resource, cluster_tag, resource_name, service_type)
    logger.info(f'{action} {len(func_resource_list)} cluster zombies resources in region {region}:')
    notify_data = {}
    delete_data = {}
    cluster_data = {}
    zombie_cluster_common_methods = ZombieClusterCommonMethods(region=region)
    for func in func_resource_list:
        resource_data, cluster_left_out_days = func()
        if resource_data:
            notify_data, delete_data, cluster_data = zombie_cluster_common_methods.collect_notify_cluster_data(
                resource_data=resource_data,
                cluster_left_out_days=cluster_left_out_days,
                notify_data=notify_data, delete_data=delete_data, cluster_data=cluster_data, func_name=func.__name__)
            resource_data_list = sorted(set(resource_data.values()))
            resource_data_list = [func.__name__.replace("zombie_cluster_", "") + ':' + item for item in
                                  resource_data_list]
            logger.info(f'key: {func.__name__}, count: {len(resource_data)}, data: {resource_data_list}')
            zombie_result[func.__name__] = {'count': len(resource_data), 'data': resource_data_list}
            all_cluster_data.extend(resource_data_list)
    zombie_cluster_common_methods.send_mails_to_cluster_user(notify_data=notify_data, delete_data=delete_data,
                                                             cluster_data=cluster_data)
    zombie_result['all_cluster_data'] = {'count': len(set(all_cluster_data)), 'data': set(sorted(all_cluster_data))}
    return zombie_result
