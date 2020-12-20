import boto3

region = 'us-east-2'


# response = client.get_servers()
# results = response["serverList"]
# while "NextToken" in response:
#     response = client.get_servers(NextToken=response["NextToken"])
#     results.extend(response["serverList"])


class ClusterResources:

    def __init__(self, cluster_prefix, cluster_name):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.cluster_key = f'{self.cluster_prefix}{self.cluster_name}'

    def __generate_cluster_resources_list_by_tag(self, resources_list, input_resource_id, tags='Tags'):
        """
        This method return resource list that related to input resource id according to cluster's tag name
        """
        result_resources_list = []
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get(tags):
                for tag in resource[tags]:
                    if tag['Key'] == self.cluster_key:
                        result_resources_list.append(resource_id)
        return result_resources_list

    def __generate_cluster_resources_list_by_vpc(self, resources_list, input_resource_id):
        """
        This method return resource list that related to input resource id according to cluster's vpc id
        """
        result_resources_list = []
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get('VpcId'):
                for vpc_id in self.cluster_vpc():
                    if resource.get('VpcId') == vpc_id:
                        result_resources_list.append(resource_id)
        return result_resources_list

    def cluster_instance(self):
        """
        This method return list of cluster's instance according to cluster tag name
        """
        instance_list = []
        ec2s = self.ec2_client.describe_instances()
        ec2s_data = ec2s['Reservations']
        for items in ec2s_data:
            if items.get('Instances'):
                instances = items['Instances']
            instance_list.extend(
                self.__generate_cluster_resources_list_by_tag(resources_list=instances, input_resource_id='InstanceId'))
        return instance_list

    def cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        """
        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        return self.__generate_cluster_resources_list_by_tag(resources_list=volumes_data, input_resource_id='VolumeId')

    def cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        return self.__generate_cluster_resources_list_by_tag(resources_list=images_data, input_resource_id='ImageId')

    def cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        return self.__generate_cluster_resources_list_by_tag(resources_list=snapshots_data,
                                                             input_resource_id='SnapshotId')

    def cluster_security_group(self):
        """
        This method return list of cluster's security group according to cluster tag name
        """
        security_groups = self.ec2_client.describe_security_groups()
        security_groups_data = security_groups['SecurityGroups']
        return self.__generate_cluster_resources_list_by_tag(resources_list=security_groups_data,
                                                             input_resource_id='GroupId')

    def cluster_elastic_ip(self):
        """
        This method return list of cluster's elastic ip according to cluster tag name
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        return self.__generate_cluster_resources_list_by_tag(resources_list=elastic_ips_data,
                                                             input_resource_id='AllocationId')

    def cluster_network_interface(self):
        """
        This method return list of cluster's network interface according to cluster tag name
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()
        network_interfaces_data = network_interfaces['NetworkInterfaces']
        return self.__generate_cluster_resources_list_by_tag(resources_list=network_interfaces_data,
                                                             input_resource_id='NetworkInterfaceId',
                                                             tags='TagSet')

    def cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        """
        load_balancers = self.elb_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancers']
        return self.__generate_cluster_resources_list_by_vpc(resources_list=load_balancers_data,
                                                             input_resource_id='LoadBalancerArn')
        return load_balancer_list

    def cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        return self.__generate_cluster_resources_list_by_tag(resources_list=vpcs_data,
                                                             input_resource_id='VpcId')

    def cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        return self.__generate_cluster_resources_list_by_tag(resources_list=subnets_data,
                                                             input_resource_id='SubnetId')

    def cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        return self.__generate_cluster_resources_list_by_tag(resources_list=route_tables_data,
                                                             input_resource_id='RouteTableId')

    def cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        return self.__generate_cluster_resources_list_by_tag(resources_list=internet_gateways_data,
                                                             input_resource_id='InternetGatewayId')

    def cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        return self.__generate_cluster_resources_list_by_tag(resources_list=dhcp_options_data,
                                                             input_resource_id='DhcpOptionsId')

    def cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        return self.__generate_cluster_resources_list_by_tag(resources_list=vpc_endpoints_data,
                                                             input_resource_id='VpcEndpointId')

    def cluster_nat_gateway(self):
        """
        This method return list of cluster's nat gateway according to cluster tag name
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        return self.__generate_cluster_resources_list_by_tag(resources_list=nat_gateways_data,
                                                             input_resource_id='NatGatewayId')

    def cluster_network_acl(self):
        """
        This method return list of cluster's network acl according to cluster vpc id
        """
        network_acls = self.ec2_client.describe_network_acls()
        network_acls_data = network_acls['NetworkAcls']
        return self.__generate_cluster_resources_list_by_vpc(resources_list=network_acls_data,
                                                             input_resource_id='NetworkAclId')

    def cluster_role(self):
        """
        This method return list of cluster's role according to cluster name
        """
        # tag_role
        result_role_list = []
        role_name_list = [f'{self.cluster_name}-master-role', f'{self.cluster_name}-worker-role']

        for role_name in role_name_list:
            try:
                role = self.iam_client.get_role(RoleName=f'{self.cluster_name}-master-role')
                role_data = role['Role']
                result_role_list.append(role_data['Arn'])
            except Exception:
               print(f'Missing cluster role name: {role_name}')

        return result_role_list

    def cluster_s3_bucket(self):
        """
        This method return list of cluster's s3 bucket according to cluster name
        """
        bucket_result_list = []
        response = self.s3_client.list_buckets()

        for bucket in response['Buckets']:
            if bucket['Name'].startswith(self.cluster_name):
                bucket_result_list.append(bucket['Name'])

        return bucket_result_list

