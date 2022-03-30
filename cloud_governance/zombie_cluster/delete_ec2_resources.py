import time

import typeguard
from botocore.client import BaseClient

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class DeleteEC2Resources:
    """
    This class deletes the EC2 resources
    0 dependencies
    Elastic Load Balancer
    Elastic Load Balancer v2
    volumes
    snapshots
    VPC Endpoints
    DHCP options set
    Route Table
    Security Groups
    NatGateway

    1 Dependencies
    NetworkACL [ Subnet ]

    2 Dependencies
    Network Interface [ NatGateway, Elastic Load Balancer ]
    Internet Gateway [ NatGateway, ElasticIP ]

    3 Dependencies
    Subnet [ Network Interface, NatGateway, Elastic Load Balancer ]
    Elastic Ip [ Network interface, NatGateway, Elastic Load Balancer ]

    12 Dependencies
    VPC [ Network Interface, NatGateway, Elastic Load Balancer, Vpc Endpoints, Route tables, Subnets,
          Security Groups, NetworkACl]
    """

    SLEEP_TIME = 30

    def __init__(self, client: BaseClient, elb_client: BaseClient, elbv2_client: BaseClient):
        self.client = client
        self.elb_client = elb_client
        self.elbv2_client = elbv2_client
        self.get_detail_list = Utils().get_details_resource_list

    @typeguard.typechecked
    def delete_zombie_resource(self, resource: str, resource_id: str, vpc_id: str = '',
                               deletion_type: str = '', pending_resources: dict = ''):
        """
        This method filter the resource and call to delete resource function
        :param pending_resources:
        :param delete_elip:
        :param deletion_type:
        :param resource:
        :param resource_id:
        :param vpc_id:
        :return:
        """
        if resource == 'load_balancer':
            self.__delete_load_balancer(resource_id=resource_id)
        elif resource == 'load_balancer_v2':
            self.__delete_load_balancer_v2(resource_id=resource_id)
        elif resource == 'ec2_volume':
            self.__delete_volume(resource_id=resource_id)
        elif resource == 'ebs_snapshots':
            self.__delete_snapshots(resource_id=resource_id)
        elif resource == 'vpc_endpoints':
            self.__delete_vpc_endpoints(resource_id=resource_id)
        elif resource == 'dhcp_options':
            self.__delete_dhcp_options(resource_id=resource_id, vpc_id=vpc_id)
        elif resource == 'route_table':
            self.__delete_route_table(resource_id=resource_id, vpc_id=vpc_id)
        elif resource == 'security_group':
            self.__delete_security_group(resource_id=resource_id, vpc_id=vpc_id)
        elif resource == 'nat_gateways':
            self.__delete_nat_gateways(resource_id=resource_id)
        elif resource == 'network_acl':
            self.__delete_network_acl(resource_id=resource_id, vpc_id=vpc_id)
        elif resource == 'network_interface':
            self.__delete_network_interface(resource_id=resource_id)
        elif resource == 'internet_gateway':
            self.__delete_internet_gateway(resource_id=resource_id, vpc_id=vpc_id)
        elif resource == 'subnet':
            self.__delete_subnet(resource_id=resource_id)
        elif resource == 'elastic_ip':
            self.__delete_elastic_ip(resource_id=resource_id, deletion_type=deletion_type)
        elif resource == 'vpc':
            self.__delete_vpc(resource_id=resource_id, pending_resources=pending_resources)

    @typeguard.typechecked
    def __get_cluster_references(self, resource_id: str, resource_list: list,
                                 input_resource_id: str, output_result: str):
        """
        This method get the cluster resources based on input format and output format
        :param resource_id:
        :param resource_list:
        :param input_resource_id:
        :param output_result:
        :return:
        """
        result = []
        for resource in resource_list:
            if output_result in resource:
                if input_resource_id in resource and resource.get(input_resource_id) == resource_id:
                    if isinstance(resource.get(output_result), list):
                        result.extend(resource.get(output_result))
                    else:
                        result.append(resource.get(output_result))
            elif output_result == '':
                if input_resource_id in resource and resource.get(input_resource_id) == resource_id:
                    result.append(resource)
        return result

    @typeguard.typechecked
    def __delete_load_balancer(self, resource_id: str):
        """
        Delete the Load Balancer based on LoadBalancer ID
        :param resource_id:
        :return:
        """
        try:
            self.elb_client.delete_load_balancer(LoadBalancerName=resource_id)
            logger.info(f'delete_load_balancer: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_load_balancer: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_load_balancer_v2(self, resource_id: str):
        """
        Delete the Load Balancer based on LoadBalancer ID
        :param resource_id:
        :return:
        """
        try:
            self.elbv2_client.delete_load_balancer(LoadBalancerArn=resource_id)
            logger.info(f'delete_load_balancer: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_load_balancer: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_volume(self, resource_id: str):
        try:
            self.client.delete_volume(VolumeId=resource_id)
            logger.info(f'delete_volume: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_volume: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_snapshots(self, resource_id: str):
        try:
            self.client.delete_snapshot(SnapshotId=resource_id)
            logger.info(f'delete_snapshot: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_snapshot: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_vpc_endpoints(self, resource_id: str):
        """
        This method delete the VPC endpoints based on vpc_endpoint ID
        :param resource_id:
        :return:
        """
        try:
            self.client.delete_vpc_endpoints(VpcEndpointIds=[resource_id])
            logger.info(f'delete_vpc_endpoints: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_vpc_endpoints: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_dhcp_options(self, resource_id: str, vpc_id: str = ''):
        """
        This method delete the dhcp options in the following order
        set associate dhcp options in vpc as default --> delete dhcp options
        :param resource_id:
        :return:
        """
        try:
            if vpc_id:
                self.client.associate_dhcp_options(DhcpOptionsId='default', VpcId=vpc_id)
            self.client.delete_dhcp_options(DhcpOptionsId=resource_id)
            logger.info(f'delete_dhcp_options: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_dhcp_options: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_route_table(self, resource_id: str, vpc_id: str):
        """
        This method deleted the Route Table in the following order
        Disassociate Route Tables subnets --> Route table
        :param resource_id:
        :return:
        """
        # @todo call vpc deletion
        try:
            route_tables = self.get_detail_list(func_name=self.client.describe_route_tables, input_tag='RouteTables',
                                                check_tag='NextToken')
            subnets = self.__get_cluster_references(resource_id=resource_id, resource_list=route_tables,
                                                    input_resource_id='RouteTableId',
                                                    output_result='Associations')
            main_route_table = False
            for subnet in subnets:
                if subnet.get('SubnetId'):
                    self.client.disassociate_route_table(AssociationId=subnet['RouteTableAssociationId'])
                elif subnet.get('RouteTableId') and not subnet.get('Main'):
                    self.client.disassociate_route_table(AssociationId=subnet['RouteTableAssociationId'])
                if subnet.get('Main'):
                    main_route_table = True
            if not main_route_table:
                self.client.delete_route_table(RouteTableId=resource_id)
                logger.info(f'delete_route_table: {resource_id}')
            else:
                logger.info(f'Main route table: {resource_id} is deleted by vpc: {vpc_id} ')
        except Exception as err:
            logger.exception(f'Cannot delete_route_table: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_security_group(self, resource_id: str, vpc_id: str):
        """
        This method deletes the NatGateway in the following order
        remove security group ingress --> modify security groups in Network interface --> delete security group
        :param resource_id:
        :return:
        """
        try:
            security_groups = self.get_detail_list(func_name=self.client.describe_security_groups,
                                                   input_tag='SecurityGroups', check_tag='NextToken')
            vpc_security_groups = self.__get_cluster_references(resource_id=vpc_id, resource_list=security_groups,
                                                                input_resource_id='VpcId',
                                                                output_result='')
            for vpc_security_group in vpc_security_groups:
                if vpc_security_group.get('IpPermissions'):
                    self.client.revoke_security_group_ingress(GroupId=vpc_security_group.get('GroupId'),
                                                              IpPermissions=vpc_security_group.get('IpPermissions'))

            network_interfaces = self.get_detail_list(func_name=self.client.describe_network_interfaces,
                                                      input_tag='NetworkInterfaces', check_tag='NextToken')
            network_interface_ids = self.__get_cluster_references(resource_id=vpc_id, resource_list=network_interfaces,
                                                                  input_resource_id='VpcId',
                                                                  output_result='')

            default_security_group_id = [security_group.get('GroupId') for security_group in vpc_security_groups
                                         if security_group.get('GroupName') == 'default'][0]
            for network_interface in network_interface_ids:
                for security_group in network_interface.get('Groups'):
                    if security_group.get('GroupId') == resource_id and default_security_group_id != security_group.get('GroupId'):
                        self.client.modify_network_interface_attribute(Groups=[default_security_group_id],
                                                                       NetworkInterfaceId=network_interface.get(
                                                                           'NetworkInterfaceId'))
            if resource_id == default_security_group_id:
                logger.info(f'default security group: {resource_id} is deleted by vpc: {vpc_id} ')
            else:
                self.client.delete_security_group(GroupId=resource_id)
                logger.info(f'delete_security_group: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_security_group: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_nat_gateways(self, resource_id: str):
        """
        This method delete the NatGateway based on NatGateway ID
        :param resource_id:
        :return:
        """
        try:
            nat_gateway = self.client.describe_nat_gateways(
                Filter=[{'Name': 'nat-gateway-id', 'Values': [resource_id]}])['NatGateways'][0]
            if nat_gateway.get('State') == 'available':
                self.client.delete_nat_gateway(NatGatewayId=resource_id)
                while nat_gateway.get('State') != 'deleted':
                    nat_gateway = self.client.describe_nat_gateways(
                        Filter=[{'Name': 'nat-gateway-id', 'Values': [resource_id]}])['NatGateways'][0]
                    time.sleep(self.SLEEP_TIME)
                logger.info(f'delete_nat_gateway: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_nat_gateway: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_network_acl(self, resource_id, vpc_id: str):
        try:
            nacls = self.get_detail_list(func_name=self.client.describe_network_acls,
                                         input_tag='NetworkAcls', check_tag='NextToken')
            vpc_nacls = self.__get_cluster_references(resource_id=resource_id, resource_list=nacls,
                                                      input_resource_id='NetworkAclId', output_result='Associations')
            default_nacl = self.__get_cluster_references(resource_id=resource_id, resource_list=nacls,
                                                         input_resource_id='NetworkAclId', output_result='IsDefault')
            if default_nacl:
                default_nacl = default_nacl[0]
                for vpc_nacl in vpc_nacls:
                    self.__delete_subnet(resource_id=vpc_nacl['SubnetId'])
                if not default_nacl:
                    self.client.delete_network_acl(NetworkAclId=resource_id)
                    logger.info(f'delete_network_acl: {resource_id}')
                else:
                    logger.info(f'default network acl: {resource_id} is deleted by vpc: {vpc_id} ')
        except Exception as err:
            logger.exception(f'Cannot delete_network_acl: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_network_interface(self, resource_id: str):
        """
        This method deletes the Network Interface in the following order
        Load balancer / NatGateway --> Release Elastic IPs --> detach Network Interface --> Delete Network Interface
        :param resource_id:
        :return:
        """
        try:
            resource_list = self.get_detail_list(func_name=self.client.describe_network_interfaces,
                                                 input_tag='NetworkInterfaces', check_tag='NextToken')
            descriptions = self.__get_cluster_references(resource_id=resource_id, resource_list=resource_list,
                                                         input_resource_id='NetworkInterfaceId',
                                                         output_result="Description")
            delete = False
            if descriptions:
                for description in descriptions:
                    if "ELB" in description:
                        self.__delete_load_balancer(description.split(" ")[-1])
                    elif "NAT" in description:
                        self.__delete_nat_gateways(resource_id=description.split(" ")[-1])
                        delete = True
            if resource_list and not delete:
                attachments = self.__get_cluster_references(resource_id=resource_id, resource_list=resource_list,
                                                            input_resource_id='NetworkInterfaceId',
                                                            output_result='Attachment')
                if attachments:
                    self.client.detach_network_interface(AttachmentId=attachments[0]['AttachmentId'])
                self.client.delete_network_interface(NetworkInterfaceId=resource_id)
                logger.info(f'delete_network_interface: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot disassociate_address: {resource_id}, {err}')

    @typeguard.typechecked
    def network_interface(self, subnet_id: str = ''):
        """
        This method calls delete interface method if subnet is used by network interface
        :param subnet_id:
        :return:
        """
        network_interfaces = self.get_detail_list(func_name=self.client.describe_network_interfaces,
                                                  input_tag='NetworkInterfaces', check_tag='NextToken')
        network_interface_ids = self.__get_cluster_references(resource_id=subnet_id,
                                                              resource_list=network_interfaces,
                                                              input_resource_id='SubnetId',
                                                              output_result="NetworkInterfaceId")
        for network_interface_id in network_interface_ids:
            if subnet_id:
                self.__delete_network_interface(resource_id=network_interface_id)

    @typeguard.typechecked
    def __delete_internet_gateway(self, resource_id: str, vpc_id: str):
        """
        This method delete Internet gateway in the following order
        NatGateway( Delete Network Interface associated with It ) --> Release Address --> Internet Gateway
        :param resource_id:
        :param vpc_id:
        :return:
        """
        try:
            network_interfaces = self.get_detail_list(func_name=self.client.describe_network_interfaces,
                                                      input_tag='NetworkInterfaces', check_tag='NextToken')
            network_interface_ids = self.__get_cluster_references(resource_id=vpc_id, resource_list=network_interfaces,
                                                                  input_resource_id='VpcId',
                                                                  output_result='NetworkInterfaceId')

            for network_interface_id in network_interface_ids:
                self.__delete_network_interface(resource_id=network_interface_id)
            if vpc_id:
                self.client.detach_internet_gateway(InternetGatewayId=resource_id, VpcId=vpc_id)
            self.client.delete_internet_gateway(InternetGatewayId=resource_id)
            logger.info(f'delete_internet_gateway: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_internet_gateway: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_subnet(self, resource_id: str):
        """
        This method delete the Subnets in the following order
        Network Interface --> Subnet
        :param resource_id:
        :return:
        """
        try:
            self.network_interface(subnet_id=resource_id)
            self.client.delete_subnet(SubnetId=resource_id)
            logger.info(f'delete_subnet: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_subnet: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_elastic_ip(self, resource_id: str, deletion_type: str):
        """
        This method delete Elastic Ip in the following order
        Network Interface --> Release IP
        :param resource_id:
        :return:
        """
        try:
            if deletion_type:
                elastic_ips = self.client.describe_addresses()['Addresses']
                network_interfaces = self.__get_cluster_references(resource_id=resource_id, resource_list=elastic_ips,
                                                                   input_resource_id='AssociationId',
                                                                   output_result='NetworkInterfaceId')
                for network_interface in network_interfaces:
                    self.__delete_network_interface(network_interface)
            else:
                self.client.release_address(AllocationId=resource_id)
                logger.info(f'release_address: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot release_address: {resource_id}, {err}')

    @typeguard.typechecked
    def __delete_vpc(self, resource_id: str, pending_resources: dict):
        """
        This method delete the vpc in the following order
        NatGateway -> Network Interface -> Security groups --> VPC Endpoints --> Route Tables --> Network Acls --> vpc
        :param resource_id:
        :param pending_resources:
        :return:
        """
        try:
            i = 0
            for key, pending_resource in pending_resources.items():
                pending_resource(resource_id)
            vpc_peerings = self.client.describe_vpc_peering_connections()['VpcPeeringConnections']
            for vpc_peering in vpc_peerings:
                if vpc_peering.get('Status').get('Code') == 'active':
                    if vpc_peering.get('RequesterVpcInfo').get('VpcId') == resource_id:
                        self.client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpc_peering.get('VpcPeeringConnectionId'))
                    elif vpc_peering.get('AccepterVpcInfo').get('VpcId') == resource_id:
                        self.client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpc_peering.get('VpcPeeringConnectionId'))
                elif vpc_peering.get('Status').get('Code') == 'pending-acceptance':
                    if vpc_peering.get('RequesterVpcInfo').get('VpcId') == resource_id:
                        self.client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpc_peering.get('VpcPeeringConnectionId'))

            self.client.delete_vpc(VpcId=resource_id)
            logger.info(f'delete_vpc: {resource_id}')
        except Exception as err:
            logger.exception(f'Cannot delete_vpc: {resource_id}, {err}')
