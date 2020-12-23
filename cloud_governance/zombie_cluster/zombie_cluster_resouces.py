import boto3
from cloud_governance.common.logger.init_logger import logger


region = 'us-east-2'

# @todo add next token
# response = client.get_servers()
# results = response["serverList"]
# while "NextToken" in response:
#     response = client.get_servers(NextToken=response["NextToken"])
#     results.extend(response["serverList"])


class ZombieClusterResources:
    """
    This class filter zombie cluster resources
    """

    def __init__(self, cluster_prefix: str = None):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix

    def __cluster_instance(self):
        """
        This method return list of cluster's instance according to cluster tag name
        :return:
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

    def __get_cluster_resources(self, resources_list: list, input_resource_id: str, tags='Tags'):
        """
        This method return all cluster resources keys that start with cluster prefix
        :param resources_list:
        :param tags:
        :return: dictionary of the resources key and id
        """
        result_resources_key_id = {}
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get(tags):
                for tag in resource[tags]:
                    if tag['Key'].startswith(self.cluster_prefix):
                        result_resources_key_id[resource_id] = tag['Key']
        return result_resources_key_id

    def __get_zombie_resources(self, exist_resources: dict):
        zombie_resources = []
        zombies_values = set(exist_resources.values()) - set(self.__cluster_instance().values())
        for zombie_value in zombies_values:
            for key, value in exist_resources.items():
                if zombie_value == value:
                    zombie_resources.append(key)
        return zombie_resources

    def zombie_cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        """

        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        exist_volume = self.__get_cluster_resources(resources_list=volumes_data, input_resource_id='VolumeId')
        return self.__get_zombie_resources(exist_volume)

    def zombie_cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        exist_ami = self.__get_cluster_resources(resources_list=images_data, input_resource_id='ImageId')
        return self.__get_zombie_resources(exist_ami)

    def zombie_cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        exist_snapshot = self.__get_cluster_resources(resources_list=snapshots_data,
                                                             input_resource_id='SnapshotId')
        return self.__get_zombie_resources(exist_snapshot)

    def zombie_cluster_security_group(self):
        """
        This method return list of zombie cluster's security groups compare to existing instances
        :return: list of zombie cluster's security groups
        """
        security_groups = self.ec2_client.describe_security_groups()
        exist_security_group = self.__get_cluster_resources(resources_list=security_groups['SecurityGroups'],
                                            input_resource_id='GroupId')
        return self.__get_zombie_resources(exist_security_group)

    def zombie_cluster_elastic_ip(self):
        """
        This method return list of zombie cluster's elastic ip according to existing instances
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        exist_elastic_ip = self.__get_cluster_resources(resources_list=elastic_ips_data,
                                                             input_resource_id='AllocationId')
        return self.__get_zombie_resources(exist_elastic_ip)

    def zombie_cluster_network_interface(self):
        """
        This method return list of zombie cluster's network interface according to existing instances
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()
        network_interfaces_data = network_interfaces['NetworkInterfaces']
        exist_network_interface = self.__get_cluster_resources(resources_list=network_interfaces_data,
                                                             input_resource_id='NetworkInterfaceId',
                                                             tags='TagSet')
        return self.__get_zombie_resources(exist_network_interface)

    def zombie_cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
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
                            exist_load_balancer[resource_id] = tag['Key']
                            break
        return self.__get_zombie_resources(exist_load_balancer)

    def zombie_cluster_load_balancer_v2(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
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
                            exist_load_balancer[resource_id] = tag['Key']
                            break
        return self.__get_zombie_resources(exist_load_balancer)

    def __get_all_exist_vpcs(self):
        """
        This method return all exist vpc ids (for supporting Network ACL - missing OpenShift tags)
        :return:
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        vpcs_list = []
        for resource in vpcs_data:
            vpcs_list.append(resource['VpcId'])
        return vpcs_list

    def zombie_cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        exist_vpc = self.__get_cluster_resources(resources_list=vpcs_data,
                                                             input_resource_id='VpcId')
        return self.__get_zombie_resources(exist_vpc)

    def zombie_cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        exist_subnet = self.__get_cluster_resources(resources_list=subnets_data,
                                                             input_resource_id='SubnetId')
        return self.__get_zombie_resources(exist_subnet)

    def zombie_cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        exist_route_table = self.__get_cluster_resources(resources_list=route_tables_data,
                                                             input_resource_id='RouteTableId')
        return self.__get_zombie_resources(exist_route_table)

    def zombie_cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        exist_internet_gateway = self.__get_cluster_resources(resources_list=internet_gateways_data,
                                                             input_resource_id='InternetGatewayId')
        return self.__get_zombie_resources(exist_internet_gateway)

    def zombie_cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        exist_dhcp_option = self.__get_cluster_resources(resources_list=dhcp_options_data,
                                                             input_resource_id='DhcpOptionsId')
        return self.__get_zombie_resources(exist_dhcp_option)

    def zombie_cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        exist_vpc_endpoint = self.__get_cluster_resources(resources_list=vpc_endpoints_data,
                                                             input_resource_id='VpcEndpointId')
        return self.__get_zombie_resources(exist_vpc_endpoint)

    def zombie_cluster_nat_gateway(self):
        """
        This method return list of zombie cluster's nat gateway according to cluster tag name
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        exist_nat_gateway = self.__get_cluster_resources(resources_list=nat_gateways_data,
                                                             input_resource_id='NatGatewayId')
        return self.__get_zombie_resources(exist_nat_gateway)

    def zombie_network_acl(self):
        """
        This method return list of zombie cluster's network acl according to existing vpc id
        """
        exist_network_acl = {}
        network_acls = self.ec2_client.describe_network_acls()
        network_acls_data = network_acls['NetworkAcls']
        for resource in network_acls_data:
            exist_network_acl[resource['NetworkAclId']] = resource['VpcId']
        zombie_resources = []
        all_exist_vpcs = self.__get_all_exist_vpcs()
        zombies_values = set(exist_network_acl.values()) - set(all_exist_vpcs)
        for zombie_value in zombies_values:
            for key, value in exist_network_acl.items():
                if zombie_value == value:
                    zombie_resources.append(key)
        return zombie_resources

    def zombie_cluster_role(self):
        """
        This method return list of cluster's role according to cluster name
        """
        exist_role_name_tag = {}
        roles = self.iam_client.list_roles()
        roles_data = roles['Roles']
        for role in roles_data:
            role_name = role['RoleName']
            role_data = self.iam_client.get_role(RoleName=role_name)
            data = role_data['Role']
            if data.get('Tags'):
                for tag in data['Tags']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        exist_role_name_tag[role_name] = tag['Key']
        return self.__get_zombie_resources(exist_role_name_tag)

    def zombie_cluster_s3_bucket(self, cluster_stamp: str = 'image-registry'):
        """
        This method return list of cluster's s3 bucket according to cluster name
        """
        bucket_name_list = []
        bucket_result_list = []
        cluster_instance_tag_list = []
        response = self.s3_client.list_buckets()

        for bucket in response['Buckets']:
            if cluster_stamp in bucket['Name']:
                bucket_name_list.append(bucket['Name'])
        exist_cluster_instance = self.__cluster_instance()

        # Get all cluster instance name without cluster prefix
        for cluster_instance_tag in exist_cluster_instance.values():
            for value in cluster_instance_tag:
                cluster_instance_tag_list.append(value.replace(self.cluster_prefix, ''))

        # find all buckets that contains cluster name
        for bucket_name in bucket_name_list:
            for cluster_name in cluster_instance_tag_list:
                if cluster_name in bucket_name:
                    bucket_result_list.append(bucket_name)

        return bucket_result_list



