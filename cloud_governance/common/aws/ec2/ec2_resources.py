import boto3
import typeguard

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class EC2_Resources:

    def __init__(self):
        self.elb1_client = boto3.client('elb')
        self.elbv2_client = boto3.client('elbv2')
        self.ec2_client = boto3.client('ec2')
        self.get_full_list = Utils().get_details_resource_list

    @logger_time_stamp
    @typeguard.typechecked
    def find_load_balancer(self, elb_name: str):
        # elbs = self.get_full_list()
        elbs = self.elb1_client.describe_load_balancers()
        for elb in elbs['LoadBalancerDescriptions']:
            if elb['LoadBalancerName'] == elb_name:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_load_balancer_v2(self, elb_name: str):
        elbs = self.elbv2_client.describe_load_balancers()
        for elb in elbs['LoadBalancers']:
            if elb['LoadBalancerName'] == elb_name:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_vpc_endpoints(self, vpc_endpoint_id: str):
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        for vpc_endpoint in vpc_endpoints['VpcEndpoints']:
            if vpc_endpoint['VpcEndpointId'] == vpc_endpoint_id:
                if vpc_endpoint['State'] == 'deleted':
                    return True
        return False

    def find_volume(self):
        volumes = self.ec2_client.describe_volumes()
        if len(volumes['Volumes']) == 0:
            return True
        return False

    def find_dhcp_options(self):
        dhcp_options = self.ec2_client.describe_dhcp_options()
        if len(dhcp_options['DhcpOptions']) == 0:
            return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_snapshots(self, snapshot_id: str):
        snapshots = self.ec2_client.describe_snapshots()
        for snapshot in snapshots['Snapshots']:
            if snapshot['SnapshotId'] == snapshot_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_route_table(self, route_table_id: str):
        route_tables = self.ec2_client.describe_route_tables()
        for route_table in route_tables['RouteTables']:
            if route_table['RouteTableId'] == route_table_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_security_group(self, security_group_id: str):
        security_groups = self.ec2_client.describe_security_groups()
        for security_group in security_groups['SecurityGroups']:
            if security_group['GroupId'] == security_group_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_nat_gateway(self, nat_gateway_id: str):
        nat_gateways = self.ec2_client.describe_nat_gateways()['NatGateways']
        for nat_gateway in nat_gateways:
            if nat_gateway['NatGatewayId'] == nat_gateway_id:
                if nat_gateway['State'] == 'deleted':
                    return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_network_acl(self, network_acl_id: str):
        network_acls = self.ec2_client.describe_network_acls()['NetworkAcls']
        for network_acl in network_acls:
            if network_acl['NetworkAclId'] == network_acl_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_network_interface(self, network_interface_id: str):
        network_interfaces = self.ec2_client.describe_network_interfaces()['NetworkInterfaces']
        for network_interface in network_interfaces:
            if network_interface['NetworkInterfaceId'] == network_interface_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_internet_gateway(self, ing_id: str):
        internet_gateways = self.ec2_client.describe_network_interfaces()['NetworkInterfaces']
        for internet_gateway in internet_gateways:
            if internet_gateway['InternetGatewayId'] == ing_id:
                return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_subnet(self, subnet_id: str):
        subnets = self.ec2_client.describe_subnets()['Subnets']
        for subnet in subnets:
            if subnet['SubnetId'] == subnet_id:
                return True
        return False

    def find_elastic_ip(self):
        elastic_ips = self.ec2_client.describe_addresses()['Addresses']
        if len(elastic_ips) == 0:
            return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_vpc(self, cluster_tag: str):
        vpcs = self.ec2_client.describe_vpcs()['Vpcs']
        for vpc in vpcs:
            if vpc.get('tags'):
                for tag in vpc.get('Tags'):
                    if tag['Key'] == cluster_tag:
                        return True
        return False

    @logger_time_stamp
    @typeguard.typechecked
    def find_ami(self, image_id: str):
        images = self.ec2_client.describe_images(Owners=['self'])
        for image in images['Images']:
            if image['ImageId'] == image_id:
                return True
        return False
