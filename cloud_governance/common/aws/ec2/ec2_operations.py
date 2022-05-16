import boto3
import typeguard

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class EC2Operations:
    """
    This class is useful for writing EC2 Operations
    """

    def __init__(self, region: str = 'us-east-2'):
        """
        Initializing the AWS resources
        """
        self.elb1_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.get_full_list = Utils().get_details_resource_list

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
    def scan_cluster_non_cluster_resources(self, resources: list):
        """
        This method returns the list of cluster and non-cluster resources.
        @param resources:
        @return:
        """
        cluster = []
        non_cluster = []
        for resource in resources:
            found = False
            if resource.get('Tags'):
                for tag in resource.get('Tags'):
                    if 'kubernetes.io/cluster/' in tag.get('Key'):
                        found = True
                        break
            if found:
                cluster.append(resource)
            else:
                non_cluster.append(resource)
        return [cluster, non_cluster]
