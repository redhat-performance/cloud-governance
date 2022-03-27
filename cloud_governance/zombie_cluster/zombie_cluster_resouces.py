import boto3
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.aws.utils.utils import Utils


# @todo add next token
# response = client.get_servers()
# results = response["serverList"]
# while "NextToken" in response:
#     response = client.get_servers(NextToken=response["NextToken"])
#     results.extend(response["serverList"])
from cloud_governance.zombie_cluster.delete_ec2_resources import DeleteEC2Resources
from cloud_governance.zombie_cluster.delete_iam_resources import DeleteIAMResources
from cloud_governance.zombie_cluster.delete_s3_resources import DeleteS3Resources


class ZombieClusterResources:
    """
    This class filter zombie cluster resources
    """

    def __init__(self, cluster_prefix: str = None, delete: bool = False, region: str = 'us-east-2',
                 cluster_tag: str = '', resource_name: str = ''):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.cluster_prefix = cluster_prefix
        self.delete = delete
        self.cluster_tag = cluster_tag
        self.resource_name = resource_name
        self.delete_ec2_resource = DeleteEC2Resources(self.ec2_client, self.elb_client, self.elbv2_client)
        self.delete_iam_resource = DeleteIAMResources(iam_client=self.iam_client)
        self.delete_s3_resource = DeleteS3Resources(s3_client=self.s3_client, s3_resource=self.s3_resource)
        self.__get_details_resource_list = Utils().get_details_resource_list


    def _all_cluster_instance(self):
        """
        This method return list of cluster's instance tag name that contains openshift tag prefix from all regions
        :return: list of cluster's instance tag name
        """
        instances_list = []
        result_instance = {}
        regions_data = self.ec2_client.describe_regions()
        for region in regions_data['Regions']:
            self.__ec2 = boto3.client('ec2', region_name=region['RegionName'])
            ec2s = self.__ec2.describe_instances()
            ec2s_data = ec2s['Reservations']
            for items in ec2s_data:
                if items.get('Instances'):
                    instances_list.append(items['Instances'])
            for instance in instances_list:
                for item in instance:
                    if item.get('InstanceId'):
                        instance_id = item['InstanceId']
                    if item.get('Tags'):
                        for tag in item['Tags']:
                            if tag['Key'].startswith(self.cluster_prefix):
                                result_instance[instance_id] = tag['Key']
        return result_instance

    def _cluster_instance(self):
        """
        This method return list of cluster's instance tag name that contains openshift tag prefix
        :return: list of cluster's instance tag name
        """
        instances_list = []
        result_instance = {}
        ec2s = self.ec2_client.describe_instances()
        ec2s_data = ec2s['Reservations']
        for items in ec2s_data:
            if items.get('Instances'):
                instances_list.append(items['Instances'])
        for instance in instances_list:
            for item in instance:
                if item.get('InstanceId'):
                    instance_id = item['InstanceId']
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if tag['Key'].startswith(self.cluster_prefix):
                            result_instance[instance_id] = tag['Key']

        return result_instance

    def __get_cluster_resources(self, resources_list: list, input_resource_id: str, tags: str = 'Tags'):
        """
        This method return all cluster resources keys that start with cluster prefix
        :param resources_list:
        :param tags:
        :return: dictionary of the resources key and id
        """
        result_resources_key_id = {}
        for resource in resources_list:
            if resource.get(input_resource_id):
                resource_id = resource[input_resource_id]
            # skip when input_resource_id no found
            else:
                continue
            if resource.get(tags):
                for tag in resource[tags]:
                    if tag['Key'].startswith(self.cluster_prefix):
                        # when input a specific cluster, return resource id of the input cluster
                        for inner_tag in resource[tags]:
                            if self.cluster_tag:
                                if self.cluster_tag == inner_tag['Key']:
                                    result_resources_key_id[resource_id] = tag['Key']
                            elif self.resource_name:
                                if self.resource_name == inner_tag['Value']:
                                    result_resources_key_id[resource_id] = tag['Key']
                            else:
                                result_resources_key_id[resource_id] = tag['Key']
                        break
        return result_resources_key_id

    def __extract_vpc_id_from_resource_data(self, zombie_id: str, resource_data: list, input_tag: str, output_tag: str =''):
        vpc_id = ''
        for resource in resource_data:
            if resource.get(input_tag) == zombie_id:
                if output_tag:
                    vpc_id = resource.get(output_tag)[0].get('VpcId')
                elif resource[input_tag] == zombie_id:
                    vpc_id = resource.get('VpcId')
        return vpc_id

    def __get_cluster_resources_by_vpc_id(self, vpc_id: str, resource_data: list, output_tag: str, input_tag: str = ''):
        ids = []
        for resource in resource_data:
            if input_tag:
                if resource.get(input_tag)[0].get('VpcId') == vpc_id:
                    ids.append(resource.get(output_tag))
            elif resource.get('VpcId') == vpc_id:
                ids.append(resource.get(output_tag))
        return ids

    def __get_zombie_resources(self, exist_resources: dict):
        """
        This method filter zombie resource, meaning no active instance for this cluster
        """
        zombie_resources = {}
        zombies_values = set(exist_resources.values()) - set(self._cluster_instance().values())

        for zombie_value in zombies_values:
            for key, value in exist_resources.items():
                if zombie_value == value:
                    zombie_resources[key] = value

        return zombie_resources

    def __get_all_zombie_resources(self, exist_resources: dict):
        """
        This method filter zombie resource, meaning no active instance for this cluster in all regions
        """
        zombie_resources = {}
        zombies_values = set(exist_resources.values()) - set(self._all_cluster_instance().values())

        for zombie_value in zombies_values:
            for key, value in exist_resources.items():
                if zombie_value == value:
                    zombie_resources[key] = value
        return zombie_resources

    def zombie_cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name and cluster name data
        delete only available resource that related to cluster
        """
        available_volumes = []
        volumes_data = self.__get_details_resource_list(self.ec2_client.describe_volumes, input_tag='Volumes',
                                                        check_tag='NextToken')
        # filter in-use resource
        for volume in volumes_data:
            if volume['State'] == 'available':
                available_volumes.append(volume)
        exist_volume = self.__get_cluster_resources(resources_list=available_volumes, input_resource_id='VolumeId')
        zombies = self.__get_zombie_resources(exist_volume)

        if zombies and self.delete:
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource_id=zombie, resource='ec2_volume')
        return zombies

    def zombie_cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name and cluster name data
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        exist_ami = self.__get_cluster_resources(resources_list=images_data, input_resource_id='ImageId')
        zombies = self.__get_zombie_resources(exist_ami)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.deregister_image(ImageId=zombie)
                    logger.info(f'deregister_image: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot deregister_image: {zombie}, {err}')
        return zombies

    def zombie_cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name and cluster name data
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        exist_snapshot = self.__get_cluster_resources(resources_list=snapshots_data,
                                                      input_resource_id='SnapshotId')
        zombies = self.__get_zombie_resources(exist_snapshot)
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource='ebs_snapshots', resource_id=zombie)
        return zombies

    def zombie_cluster_security_group(self):
        """
        This method return list of zombie cluster's security groups compare to existing instances and cluster name data
        :return: list of zombie cluster's security groups
        """
        security_groups = self.__get_details_resource_list(func_name=self.ec2_client.describe_security_groups,
                                                           input_tag='SecurityGroups', check_tag='NextToken')
        exist_security_group = self.__get_cluster_resources(resources_list=security_groups,
                                                            input_resource_id='GroupId')
        zombies = self.__get_zombie_resources(exist_security_group)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=security_groups,
                                                              input_tag='GroupId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=security_groups,
                                                                output_tag='GroupId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource('security_group', resource_id=zombie, vpc_id=vpc_id)
        return zombies

    def zombie_cluster_elastic_ip(self):
        """
        This method return list of zombie cluster's elastic ip according to existing instances and cluster name data
        """
        exist_elastic_ip_association = []
        exist_elastic_ip_allocation = []
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        for elastic_ip in elastic_ips_data:
            if elastic_ip.get('AssociationId'):
                exist_elastic_ip_association.append(elastic_ip)
            if elastic_ip.get('AllocationId'):
                exist_elastic_ip_allocation.append(elastic_ip)
        exist_elastic_ip_ass = self.__get_cluster_resources(resources_list=exist_elastic_ip_association,
                                                            input_resource_id='AssociationId')
        exist_elastic_ip_all = self.__get_cluster_resources(resources_list=exist_elastic_ip_allocation,
                                                            input_resource_id='AllocationId')
        zombies_ass = self.__get_zombie_resources(exist_elastic_ip_ass)
        zombies_all = self.__get_zombie_resources(exist_elastic_ip_all)
        if zombies_ass and self.delete:
            for zombie in zombies_ass:
                self.delete_ec2_resource.delete_zombie_resource(resource='elastic_ip', resource_id=zombie, deletion_type='disassociate')
        if zombies_all and self.delete:
            for zombie in zombies_all:
                self.delete_ec2_resource.delete_zombie_resource(resource='elastic_ip', resource_id=zombie)
        zombies = {**zombies_all}
        return zombies

    def zombie_cluster_network_interface(self):
        """
        This method return list of zombie cluster's network interface according to existing instances and cluster name data
        """
        network_interfaces_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_network_interfaces,
                                                                   input_tag='NetworkInterfaces', check_tag='NextToken')
        exist_network_interface = self.__get_cluster_resources(resources_list=network_interfaces_data,
                                                               input_resource_id='NetworkInterfaceId',
                                                               tags='TagSet')
        zombies = self.__get_zombie_resources(exist_network_interface)

        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=network_interfaces_data,
                                                              input_tag='NetworkInterfaceId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=network_interfaces_data,
                                                                output_tag='NetworkInterfaceId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource(resource='network_interface', resource_id=zombie)
        return zombies

    def zombie_cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc and cluster name data
        """

        exist_load_balancer = {}
        load_balancers = self.elb_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancerDescriptions']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerName']
            tags = self.elb_client.describe_tags(LoadBalancerNames=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if tag['Key'].startswith(self.cluster_prefix):
                            # when input a specific cluster, return resource id of the input cluster
                            if self.cluster_tag:
                                if self.cluster_tag == tag['Key']:
                                    exist_load_balancer[resource_id] = tag['Key']
                            else:
                                exist_load_balancer[resource_id] = tag['Key']
                            break
        zombies = self.__get_zombie_resources(exist_load_balancer)
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource='load_balancer', resource_id=zombie)
        return zombies

    def zombie_cluster_load_balancer_v2(self):
        """
        This method return list of cluster's load balancer according to cluster vpc and cluster name data
        """
        exist_load_balancer = {}
        load_balancers = self.elbv2_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancers']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerArn']
            tags = self.elbv2_client.describe_tags(ResourceArns=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if tag['Key'].startswith(self.cluster_prefix):
                            # when input a specific cluster, return resource id of the input cluster
                            if self.cluster_tag:
                                if self.cluster_tag == tag['Key']:
                                    exist_load_balancer[resource_id] = tag['Key']
                            else:
                                exist_load_balancer[resource_id] = tag['Key']
                            break
        zombies = self.__get_zombie_resources(exist_load_balancer)
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource='load_balancer_v2', resource_id=zombie)
        return zombies

    def __get_all_exist_vpcs(self):
        """
        This method return all exist vpc ids (for supporting Network ACL - missing OpenShift tags)
        :return:
        """
        vpcs_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_vpcs, input_tag='Vpcs',
                                                     check_tag='NextToken')
        vpcs_list = []
        for resource in vpcs_data:
            vpcs_list.append(resource['VpcId'])
        return vpcs_list

    def zombie_cluster_vpc(self, ):
        """
        This method return list of cluster's vpc according to cluster tag name and cluster name data
        """
        vpcs_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_vpcs, input_tag='Vpcs',
                                                     check_tag='NextToken')
        exist_vpc = self.__get_cluster_resources(resources_list=vpcs_data,
                                                 input_resource_id='VpcId')
        zombies = self.__get_zombie_resources(exist_vpc)
        delete_dict = {"ELB": self.zombie_cluster_load_balancer, "ELBV2": self.zombie_cluster_load_balancer_v2,
                       "VPCE": self.zombie_cluster_vpc_endpoint, "DHCP": self.zombie_cluster_dhcp_option,
                       "RT": self.zombie_cluster_route_table, "SG": self.zombie_cluster_security_group,
                       "NATG": self.zombie_cluster_nat_gateway, "NACL": self.zombie_network_acl,
                       "ENI": self.zombie_cluster_network_interface, "IGW": self.zombie_cluster_internet_gateway,
                       "SUB": self.zombie_cluster_subnet, "EIP": self.zombie_cluster_elastic_ip}
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource='vpc', resource_id=zombie,
                                                                pending_resources=delete_dict)
        return zombies

    def zombie_cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name and cluster name data
        """
        subnets_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_subnets, input_tag='Subnets',
                                                        check_tag='NextToken')
        exist_subnet = self.__get_cluster_resources(resources_list=subnets_data,
                                                    input_resource_id='SubnetId')
        zombies = self.__get_zombie_resources(exist_subnet)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=subnets_data,
                                                              input_tag='SubnetId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=subnets_data,
                                                                output_tag='SubnetId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource(resource='subnet', resource_id=zombie)
        return zombies

    def zombie_cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name and cluster name data
        """
        route_tables_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_route_tables,
                                                             input_tag='RouteTables', check_tag='NextToken')
        exist_route_table = self.__get_cluster_resources(resources_list=route_tables_data,
                                                         input_resource_id='RouteTableId')
        zombies = self.__get_zombie_resources(exist_route_table)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=route_tables_data,
                                                              input_tag='RouteTableId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=route_tables_data,
                                                                output_tag='RouteTableId')
            for zombie in zombie_ids:
                self.delete_ec2_resource.delete_zombie_resource(resource='route_table', resource_id=zombie, vpc_id=vpc_id)
        return zombies

    def zombie_cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name and cluster name data
        """
        internet_gateways_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_internet_gateways,
                                                                  input_tag='InternetGateways', check_tag='NextToken')
        exist_internet_gateway = self.__get_cluster_resources(resources_list=internet_gateways_data,
                                                              input_resource_id='InternetGatewayId')

        zombies = self.__get_zombie_resources(exist_internet_gateway)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=internet_gateways_data,
                                                              input_tag='InternetGatewayId', output_tag='Attachments')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=internet_gateways_data,
                                                                output_tag='InternetGatewayId', input_tag='Attachments')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                try:
                    self.delete_ec2_resource.delete_zombie_resource(resource='internet_gateway', resource_id=zombie,
                                                                    vpc_id=vpc_id)
                except Exception as err:
                    logger.exception(f'Cannot delete_internet_gateway: {zombie}, {err}')
        return zombies

    def zombie_cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name and cluster name data
        """
        dhcp_options_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_dhcp_options,
                                                             input_tag='DhcpOptions', check_tag='NextToken')
        exist_dhcp_option = self.__get_cluster_resources(resources_list=dhcp_options_data,
                                                         input_resource_id='DhcpOptionsId')
        zombies = self.__get_zombie_resources(exist_dhcp_option)
        if zombies and self.delete:
            vpcs = self.ec2_client.describe_vpcs()['Vpcs']
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0], resource_data=vpcs,
                                                              input_tag='DhcpOptionsId')
            for zombie in zombies:
                self.delete_ec2_resource.delete_zombie_resource(resource='dhcp_options', resource_id=zombie, vpc_id=vpc_id)
        return zombies

    def zombie_cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name and cluster name data
        """
        vpc_endpoints_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_vpc_endpoints,
                                                              input_tag='VpcEndpoints', check_tag='NextToken')
        exist_vpc_endpoint = self.__get_cluster_resources(resources_list=vpc_endpoints_data,
                                                          input_resource_id='VpcEndpointId')
        zombies = self.__get_zombie_resources(exist_vpc_endpoint)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                              resource_data=vpc_endpoints_data,
                                                              input_tag='VpcEndpointId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id,
                                                                resource_data=vpc_endpoints_data,
                                                                output_tag='VpcEndpointId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource(resource='vpc_endpoints', resource_id=zombie)
        return zombies

    def zombie_cluster_nat_gateway(self):
        """
        This method return list of zombie cluster's nat gateway according to cluster tag name and cluster name data
        """
        nat_gateways_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_nat_gateways,
                                                             input_tag='NatGateways', check_tag='NextToken')
        exist_nat_gateway = self.__get_cluster_resources(resources_list=nat_gateways_data,
                                                         input_resource_id='NatGatewayId')
        zombies = self.__get_zombie_resources(exist_nat_gateway)
        if zombies and self.delete:
            vpc_id = self.__extract_vpc_id_from_resource_data(list(zombies.keys())[0], nat_gateways_data,
                                                              input_tag='NatGatewayId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id, resource_data=nat_gateways_data,
                                                                output_tag='NatGatewayId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource(resource='nat_gateways', resource_id=zombie)
        return zombies

    def zombie_network_acl(self, vpc_id: str = ''):
        """
        This method return list of zombie cluster's network acl according to existing vpc id and cluster name data
        """
        exist_network_acl = {}
        network_acls_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_network_acls,
                                                             input_tag='NetworkAcls', check_tag='NextToken')
        for resource in network_acls_data:
            exist_network_acl[resource['NetworkAclId']] = resource['VpcId']
        zombie_resources = {}
        all_exist_vpcs = self.__get_all_exist_vpcs()
        zombies_values = set(exist_network_acl.values()) - set(all_exist_vpcs)
        for zombie_value in zombies_values:
            for key, value in exist_network_acl.items():
                if zombie_value == value:
                    zombie_resources[key] = value
        zombies = zombie_resources
        if vpc_id:
            zombies = [network_acl.get('NetworkAclId') for network_acl in network_acls_data
                       if network_acl.get('VpcId') == vpc_id]
        if zombies and self.delete:
            if not vpc_id:
                vpc_id = self.__extract_vpc_id_from_resource_data(zombie_id=list(zombies.keys())[0],
                                                                  resource_data=network_acls_data,
                                                                  input_tag='NetworkAclId')
            zombie_ids = self.__get_cluster_resources_by_vpc_id(vpc_id=vpc_id, resource_data=network_acls_data,
                                                                output_tag='NetworkAclId')
            zombie_values = zombies
            if zombie_ids:
                zombie_values = zombie_ids
            for zombie in zombie_values:
                self.delete_ec2_resource.delete_zombie_resource(resource='network_acl', resource_id=zombie, vpc_id=vpc_id)
        return zombies

    def zombie_cluster_role(self):
        """
        This method return list of cluster's role in all regions according to cluster name and cluster name data
        * Role is a global resource, need to scan for live cluster in all regions
        """
        exist_role_name_tag = {}
        roles_data = self.__get_details_resource_list(func_name=self.iam_client.list_roles, input_tag='Roles',
                                                      check_tag='Marker')
        for role in roles_data:
            role_name = role['RoleName']
            if 'worker-role' in role_name or 'master-role' in role_name:
                role_data = self.iam_client.get_role(RoleName=role_name)
                data = role_data['Role']
                if data.get('Tags'):
                    for tag in data['Tags']:
                        if tag['Key'].startswith(self.cluster_prefix):
                            # when input a specific cluster, return resource id of the input cluster
                            if self.cluster_tag:
                                if self.cluster_tag == tag['Key']:
                                    exist_role_name_tag[role_name] = tag['Key']
                            else:
                                exist_role_name_tag[role_name] = tag['Key']
                            break
        zombies = []
        if exist_role_name_tag:
            zombies = self.__get_all_zombie_resources(exist_role_name_tag)
            if zombies and self.delete:
                for zombie in zombies:
                    self.delete_iam_resource.delete_iam_zombie_resource(resource_id=zombie, resource_type='iam_role')
        return zombies

    def zombie_cluster_user(self):
        """
        This method return list of cluster's user according to cluster name and cluster name data
        * User is a global resource, need to scan for live cluster in all regions
        """
        exist_user_name_tag = {}
        users_data = self.__get_details_resource_list(func_name=self.iam_client.list_users, input_tag='Users',
                                                      check_tag='Marker')
        for user in users_data:
            user_name = user['UserName']
            user_data = self.iam_client.get_user(UserName=user_name)
            data = user_data['User']
            if data.get('Tags'):
                for tag in data['Tags']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        # when input a specific cluster, return resource id of the input cluster
                        if self.cluster_tag:
                            if self.cluster_tag == tag['Key']:
                                exist_user_name_tag[user_name] = tag['Key']
                        else:
                            exist_user_name_tag[user_name] = tag['Key']
                        break
        zombies = self.__get_all_zombie_resources(exist_user_name_tag)
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_iam_resource.delete_iam_zombie_resource(resource_id=zombie, resource_type='iam_user')
        return zombies

    def zombie_cluster_s3_bucket(self, cluster_stamp: str = 'image-registry'):
        """
        This method return list of cluster's s3 bucket according to cluster name and cluster name data
        * S3 is a global resource, need to scan for live cluster in all regions
        """
        exist_bucket_name_tag = {}
        response = self.s3_client.list_buckets()

        # Fetch all bucket with stamp
        for bucket in response['Buckets']:
            # fast filter
            if cluster_stamp in bucket['Name']:
                try:
                    tags = self.s3_client.get_bucket_tagging(Bucket=bucket['Name'])
                except Exception as e:  # continue when no bucket tags
                    continue
                for tag in tags['TagSet']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        # when input a specific cluster, return resource id of the input cluster
                        if self.cluster_tag:
                            if self.cluster_tag == tag['Key']:
                                exist_bucket_name_tag[bucket['Name']] = tag['Key']
                        else:
                            exist_bucket_name_tag[bucket['Name']] = tag['Key']
                        break
        zombies = self.__get_all_zombie_resources(exist_bucket_name_tag)
        if zombies and self.delete:
            for zombie in zombies:
                self.delete_s3_resource.delete_zombie_s3_resource(resource_type='s3_bucket', resource_id=zombie)
        return zombies

# zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False, region='us-east-2')
# print(zombie_cluster_resources.zombie_cluster_subnet())
