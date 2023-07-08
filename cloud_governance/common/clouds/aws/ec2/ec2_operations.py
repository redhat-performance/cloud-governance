import os

import boto3
import typeguard
from typing import Callable

from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class EC2Operations:
    """
    This class is useful for writing EC2 Operations
    """

    TAG_BATCHES = 20

    def __init__(self, region: str = 'us-east-2'):
        """
        Initializing the AWS resources
        """
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.elb1_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.get_full_list = Utils().get_details_resource_list
        self.utils = Utils(region=region)

    @logger_time_stamp
    @typeguard.typechecked
    def find_load_balancer(self, elb_name: str):
        """
        Find the load balancer is present or not
        :param elb_name:
        :return:
        """
        # elbs = self.get_full_list()
        elbs = self.elb1_client.describe_load_balancers()['LoadBalancerDescriptions']
        if elbs:
            for elb in elbs:
                if elb['LoadBalancerName'] == elb_name:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_load_balancer_v2(self, elb_name: str):
        """
        Find the load balancer is present or not
        :param elb_name:
        :return:
        """
        elbs = self.elbv2_client.describe_load_balancers()['LoadBalancers']
        if elbs:
            for elb in elbs:
                if elb['LoadBalancerName'] == elb_name:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_vpc_endpoints(self, vpc_endpoint_id: str):
        """
        Find the vpc endpoints present or not
        :param vpc_endpoint_id:
        :return:
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()['VpcEndpoints']
        if vpc_endpoints:
            for vpc_endpoint in vpc_endpoints:
                if vpc_endpoint['VpcEndpointId'] == vpc_endpoint_id:
                    if vpc_endpoint['State'] == 'deleted':
                        return True
            return False
        return False

    @logger_time_stamp
    def find_volume(self):
        """
        Find the volumes is present or nor
        :return:
        """
        volumes = self.ec2_client.describe_volumes()
        if len(volumes['Volumes']) == 0:
            return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_dhcp_options(self, dhcp_id: str):
        """
        Find the DHCP option present or not
        :return:
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()['DhcpOptions']
        if dhcp_options:
            for dhcp_option in dhcp_options:
                if dhcp_option['DhcpOptionsId'] == dhcp_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_snapshots(self, snapshot_id: str):
        """
        Find the snapshots present or not
        :param snapshot_id:
        :return:
        """
        snapshots = self.ec2_client.describe_snapshots()['Snapshots']
        if snapshots:
            for snapshot in snapshots:
                if snapshot['SnapshotId'] == snapshot_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_route_table(self, route_table_id: str):
        """
        Find the route table is present or not
        :param route_table_id:
        :return:
        """
        route_tables = self.ec2_client.describe_route_tables()['RouteTables']
        if route_tables:
            for route_table in route_tables:
                if route_table['RouteTableId'] == route_table_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_security_group(self, security_group_id: str):
        """
        Find the security group is present or not
        :param security_group_id:
        :return:
        """
        security_groups = self.ec2_client.describe_security_groups()['SecurityGroups']
        if security_groups:
            for security_group in security_groups:
                if security_group['GroupId'] == security_group_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_nat_gateway(self, nat_gateway_id: str):
        """
        find the nat gateway is present or not
        :param nat_gateway_id:
        :return:
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()['NatGateways']
        if nat_gateways:
            for nat_gateway in nat_gateways:
                if nat_gateway['NatGatewayId'] == nat_gateway_id:
                    if nat_gateway['State'] == 'deleted':
                        return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_network_acl(self, network_acl_id: str):
        """
        Find the network acl is present or not
        :param network_acl_id:
        :return:
        """
        network_acls = self.ec2_client.describe_network_acls()['NetworkAcls']
        if network_acls:
            for network_acl in network_acls:
                if network_acl['NetworkAclId'] == network_acl_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_network_interface(self, network_interface_id: str):
        """
        find the network interface is present or not
        :param network_interface_id:
        :return:
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()['NetworkInterfaces']
        if network_interfaces:
            for network_interface in network_interfaces:
                if network_interface['NetworkInterfaceId'] == network_interface_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_internet_gateway(self, ing_id: str):
        """
        find the internet gateway is presnt or not
        :param ing_id:
        :return:
        """
        internet_gateways = self.ec2_client.describe_network_interfaces()['NetworkInterfaces']
        if internet_gateways:
            for internet_gateway in internet_gateways:
                if internet_gateway['InternetGatewayId'] == ing_id:
                    return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_subnet(self, subnet_id: str):
        """
        find the subnet is present or not
        :param subnet_id:
        :return:
        """
        subnets = self.ec2_client.describe_subnets()['Subnets']
        if subnets:
            for subnet in subnets:
                if subnet['SubnetId'] == subnet_id:
                    return True
            return False
        return False

    @logger_time_stamp
    def find_elastic_ip(self):
        """
        find the elastic ip is present or not
        :return:
        """
        elastic_ips = self.ec2_client.describe_addresses()['Addresses']
        if len(elastic_ips) == 0:
            return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_vpc(self, cluster_tag: str):
        """
        find the vpc present or not
        :param cluster_tag:
        :return:
        """
        vpcs = self.ec2_client.describe_vpcs()['Vpcs']
        if vpcs:
            for vpc in vpcs:
                if vpc.get('tags'):
                    for tag in vpc.get('Tags'):
                        if tag['Key'] == cluster_tag:
                            return True
            return False
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_ami(self, image_id: str):
        """
        find the amazon machine image is present or not
        :param image_id:
        :return:
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        if images:
            for image in images['Images']:
                if image['ImageId'] == image_id:
                    return True
            return False
        return False

    @typeguard.typechecked
    def scan_cluster_or_non_cluster_instance(self, resources: list):
        """
        This method returns the list of cluster and non-cluster instances.
        @param resources:
        @return:
        """
        cluster = []
        non_cluster = []
        for resource in resources:
            found = False
            for item in resource:
                if item.get('Tags'):
                    for tag in item.get('Tags'):
                        if 'kubernetes.io/cluster/' in tag.get('Key'):
                            found = True
                            break
            if found:
                cluster.append(resource)
            else:
                non_cluster.append(resource)
        return [cluster, non_cluster]

    @typeguard.typechecked
    def scan_cluster_non_cluster_resources(self, resources: list, tags: str = 'Tags'):
        """
        This method returns the list of cluster and non-cluster resources.
        @param tags:
        @param resources:
        @return:
        """
        cluster = []
        non_cluster = []
        for resource in resources:
            found = False
            if resource.get(tags):
                for tag in resource.get(tags):
                    if 'kubernetes.io/cluster/' in tag.get('Key'):
                        found = True
                        break
            if found:
                cluster.append(resource)
            else:
                non_cluster.append(resource)
        return [cluster, non_cluster]

    def get_instances(self, ec2_client: boto3.client = None, **kwargs):
        """
        This method returns all instances from the region
        @return:
        """
        describe_instances = ec2_client.describe_instances if ec2_client else self.ec2_client.describe_instances
        return self.utils.get_details_resource_list(func_name=describe_instances,
                                                    input_tag='Reservations', check_tag='NextToken', **kwargs)

    def get_volumes(self, **kwargs):
        """
        This method returns all volumes in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_volumes, input_tag='Volumes',
                                                    check_tag='NextToken', **kwargs)

    def get_images(self):
        """
        This method returns all images in the region
        @return:
        """
        return self.ec2_client.describe_images(Owners=['self'])['Images']

    def get_snapshots(self):
        """
        This method returns all snapshots in the region
        @return:
        """
        return self.ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']

    def get_security_groups(self):
        """
        This method returns security groups in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_security_groups,
                                                    input_tag='SecurityGroups', check_tag='NextToken')

    def get_elastic_ips(self):
        """
        This method returns elastic_ips in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_addresses, input_tag='Addresses',
                                                    check_tag='NextToken')

    def get_network_interface(self):
        """
        This method returns network_interface in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_network_interfaces,
                                                    input_tag='NetworkInterfaces', check_tag='NextToken')

    def get_load_balancers(self):
        """
        This method returns load balancers in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.elb1_client.describe_load_balancers,
                                                    input_tag='LoadBalancerDescriptions', check_tag='Marker')

    def get_load_balancers_v2(self):
        """
        This method returns load balancers v2 in the region
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.elbv2_client.describe_load_balancers,
                                                    input_tag='LoadBalancers', check_tag='Marker')

    def get_vpcs(self):
        """
        This method returns all vpcs
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_vpcs, input_tag='Vpcs',
                                                    check_tag='NextToken')

    def get_subnets(self):
        """
        This method returns all subnets
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_subnets, input_tag='Subnets',
                                                    check_tag='NextToken')

    def get_route_tables(self):
        """
        This method returns all route tables
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_route_tables,
                                                    input_tag='RouteTables', check_tag='NextToken')

    def get_internet_gateways(self):
        """
        This method returns all internet gateways
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_internet_gateways,
                                                    input_tag='InternetGateways', check_tag='NextToken')

    def get_dhcp_options(self):
        """
        This method returns all dhcp options
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_dhcp_options,
                                                    input_tag='DhcpOptions', check_tag='NextToken')

    def get_vpce(self):
        """
        This method returns all vpc endpoints
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_vpc_endpoints,
                                                    input_tag='VpcEndpoints', check_tag='NextToken')

    def get_nat_gateways(self):
        """
        This method returns all nat gateways
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_nat_gateways,
                                                    input_tag='NatGateways', check_tag='NextToken')

    def get_nacls(self):
        """
        This method returns all network acls
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.ec2_client.describe_network_acls,
                                                    input_tag='NetworkAcls', check_tag='NextToken')

    def is_cluster_resource(self, resource_id: str):
        """
        This method checks tags have cluster key, if cluster return True else False
        @param resource_id:
        @return:
        """
        resource_tags = self.ec2_client.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [resource_id]}])
        if resource_tags.get('Tags'):
            for tag in resource_tags['Tags']:
                if 'kubernetes.io/cluster/' in tag.get('Key'):
                    return True
        return False

    def get_ec2_list(self, instances_list: list):
        """
        This method return all instances in one list by taking instances_list
        @param instances_list:
        @return:
        """
        instances = []
        for resources in instances_list:
            for resource in resources['Instances']:
                instances.append(resource)
        return instances

    def get_tag(self, name: str, tags: list):
        """
        This method get tag name fom the tags
        @param name:
        @param tags:
        @return:
        """
        if tags:
            for tag in tags:
                if tag.get('Key') == name:
                    return tag.get('Value')
        return 'NA'

    def get_global_ec2_list_by_user(self):
        """
        This method get ec2-instances based on User tag
        @return:
        """
        users_list = {}
        regions = self.ec2_client.describe_regions()['Regions']
        for region in regions:
            region_ec2_client = boto3.client('ec2', region_name=region.get('RegionName'))
            instances = self.get_ec2_list(region_ec2_client.describe_instances()['Reservations'])
            for instance in instances:
                user_data = {'InstanceId': instance.get('InstanceId'),
                             'Name': self.get_tag(name='Name', tags=instance.get('Tags')),
                             'InstanceType': instance.get('InstanceType'),
                             'LaunchTime': instance.get('LaunchTime').strftime('%Y/%m/%d %H:%M:%S'),
                             'Region': region.get('RegionName'),
                             'Account': self.__environment_variables_dict.get('account', '').upper(),
                             'State': instance.get('State')['Name']
                             }
                user = self.get_tag(name='User', tags=instance.get('Tags'))
                if user in users_list:
                    users_list[user].append(user_data)
                else:
                    users_list[user] = [user_data]
        return users_list

    def get_tag_value_from_tags(self, tags: list, tag_name: str, cast_type: str = 'str',
                                default_value: any = '') -> any:
        """
        This method return the tag value inputted by tag_name
        """
        if tags:
            for tag in tags:
                key = tag.get('Key').lower().replace("_", '').replace("-", '').strip()
                if key == tag_name.lower():
                    if cast_type:
                        if cast_type == 'int':
                            return int(tag.get('Value').strip())
                        elif cast_type == 'float':
                            return float(tag.get('Value').strip())
                        else:
                            return str(tag.get('Value').strip())
                    return tag.get('Value').strip()
        return default_value

    def get_active_regions(self):
        """
        This method return active regions in aws account
        :return:
        """
        responses = self.ec2_client.describe_regions()['Regions']
        active_regions = []
        for region in responses:
            active_regions.append(region.get('RegionName'))
        return active_regions

    def get_ec2_instance_list(self, **kwargs):
        """
        This method returns the list of instances
        :param kwargs:
        :return:
        """
        instances_list = []
        ignore_tag = kwargs.pop('ignore_tag', None)
        instances = self.get_instances(**kwargs)
        for instance in instances:
            for resource in instance['Instances']:
                skip_resource = False
                if ignore_tag:
                    for tag in resource.get('Tags', []):
                        if tag.get('Key') == ignore_tag:
                            skip_resource = True
                            break
                if not skip_resource:
                    instances_list.append(resource)
        return instances_list

    def get_ec2_instance_ids(self, **kwargs):
        """
        This method return the ec2 instance ids
        :param kwargs:
        :return:
        """
        instances = self.get_ec2_instance_list(**kwargs)
        instance_ids = []
        for instance in instances:
            instance_ids.append(instance.get('InstanceId'))
        return instance_ids

    def tag_ec2_resources(self, client_method: Callable, tags: list, resource_ids: list):
        """
        This method tag the ec2 resources with batch wise of 10
        :param client_method:
        :param tags:
        :param resource_ids:
        :return:
        """
        co = 0
        for start in range(0, len(resource_ids), self.TAG_BATCHES):
            end = start + self.TAG_BATCHES
            client_method(Resources=resource_ids[start:end], Tags=tags)
            co += 1
        return co

    def get_attached_time(self, volume_list: list):
        """
        This method return the root volume attached time
        :param volume_list:
        :return:
        """
        for mapping in volume_list:
            if mapping.get('Ebs').get('DeleteOnTermination'):
                return mapping.get('Ebs').get('AttachTime')
        return ''

    def get_active_instances(self, tag_name: str, tag_value: str, skip_full_scan: bool = False, ignore_tag: str = ''):
        """
        This method returns all active instances by filter tag_name, tag_value in all active regions
        :param ignore_tag:
        :param skip_full_scan:
        :param tag_name:
        :param tag_value:
        :return:
        """
        active_instances = {}
        active_regions = self.get_active_regions()
        for region_name in active_regions[::-1]:
            filters = [{'Name': f'tag:{tag_name}', 'Values': [tag_value, tag_value.upper(), tag_value.lower(), tag_value.title()]}]
            self.get_ec2_instance_list()
            active_instances_in_region = self.get_ec2_instance_list(Filters=filters, ec2_client=boto3.client('ec2', region_name=region_name), ignore_tag=ignore_tag)
            if active_instances_in_region:
                if skip_full_scan:
                    return True
                else:
                    active_instances[region_name] = active_instances_in_region
        return False if skip_full_scan else active_instances

    def verify_active_instances(self, tag_name: str, tag_value: str):
        """
        This method verify any active instances in all regions by tag_name, tag_value
        :param tag_name:
        :param tag_value:
        :return:
        """
        ignore_tag = 'TicketId'
        return self.get_active_instances(tag_name=tag_name, tag_value=tag_value, skip_full_scan=True, ignore_tag=ignore_tag)
