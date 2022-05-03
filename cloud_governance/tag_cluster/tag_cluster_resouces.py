import boto3
from cloud_governance.common.logger.init_logger import logger

# @todo add next token
# response = client.get_servers()
# results = response["serverList"]
# while "NextToken" in response:
#     response = client.get_servers(NextToken=response["NextToken"])
#     results.extend(response["serverList"])


class TagClusterResources:
    """
    This class filter cluster resources by cluster name, and update tags when passing input_tags
    """

    def __init__(self, cluster_name: str = None, cluster_prefix: str = None, input_tags: dict = None, region: str = 'us-east-2'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.cluster_key = self.__init_cluster_name()
        self.input_tags = input_tags

    def __init_cluster_name(self):
        """
        This method find the cluster full stamp key according to user cluster name, scan instance and if not found scan security group
        i.e.: user cluster name = test , cluster stamp key =  kubernetes.io/cluster/test-jlhpd
        :return: cluster stamp name or empty if not exist
        """
        return self.__scan_cluster_security_groups()

    def __input_tags_list_builder(self):
        """ This method build tags list according to input tags dictionary"""
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def __append_input_tags(self, current_tags: list = None):
        """
        This method append the input tags to the current tags, and return the input tags
        :param current_tags:
        :return: return concat of current tags with input tags
        """
        input_tags = self.__input_tags_list_builder()
        if current_tags:
            for current_item in current_tags:
                if self.input_tags.get(current_item['Key']):
                    for input_item in input_tags:
                        if current_item['Key'] == input_item['Key']:
                            current_item['Value'] = input_item['Value']
                else:
                    input_tags.append(current_item)
        return input_tags

    def __generate_cluster_resources_list_by_tag(self, resources_list: list, input_resource_id: str, tags: str = 'Tags'):
        """
        This method return resource list that related to input resource id according to cluster's tag name
        """
        result_resources_list = []
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get(tags):
                for tag in resource[tags]:
                    if self.cluster_key:
                        if tag['Key'] == self.cluster_key:
                            if self.input_tags:
                                all_tags = self.__append_input_tags(current_tags=resource[tags])
                                self.ec2_client.create_tags(Resources=[resource_id], Tags=all_tags)
                            result_resources_list.append(resource_id)
                    else:
                        if self.cluster_prefix in tag['Key']:
                            if self.input_tags:
                                all_tags = self.__append_input_tags(current_tags=resource[tags])
                                self.ec2_client.create_tags(Resources=[resource_id], Tags=all_tags)
                            result_resources_list.append(resource_id)
        return sorted(result_resources_list)

    def __generate_cluster_resources_list_by_vpc(self, resources_list: list, input_resource_id: str):
        """
        This method return resource list that related to input resource id according to cluster's vpc id
        """
        result_resources_list = []
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get('VpcId'):
                for vpc_id in self.cluster_vpc():
                    if resource.get('VpcId') == vpc_id:
                        if self.input_tags:
                            all_tags = self.__append_input_tags()
                            self.ec2_client.create_tags(Resources=[resource_id], Tags=all_tags)
                        result_resources_list.append(resource_id)
        return sorted(result_resources_list)

    def __scan_resource_for_cluster_fullname(self, resources_list: list, tags: str = 'Tags'):
        """
         This method scan for full cluster name according in input resource by input cluster name.
        :param resources_list:
        :param tags:
        :return:
        """
        if self.cluster_name:
            for resource in resources_list:
                if resource.get(tags):
                    for tag in resource[tags]:
                        if tag['Key'].startswith(f'{self.cluster_prefix}{self.cluster_name}'):
                            return tag['Key']
        return ''

    def __scan_cluster_security_groups(self):
        """
        This method scan for cluster stamp key in instances and security group, if not found return empty string
        :return: cluster stamp key or empty string
        """
        security_groups = self.__get_security_group_data()
        # scan security group for cluster stamp key
        return self.__scan_resource_for_cluster_fullname(resources_list=security_groups)

    def __get_instances_data(self):
        """
        This method go over all instances
        :return:
        """
        instances_list = []
        ec2s = self.ec2_client.describe_instances()
        ec2s_data = ec2s['Reservations']
        for items in ec2s_data:
            if items.get('Instances'):
                instances_list.append(items['Instances'])
        return instances_list

    def cluster_instance(self):
        """
        This method return list of cluster's instance according to cluster tag name,
        The instances list is different from other resources
        it will search for full cluster name (including random suffix string) in case of user input cluster name was given
        :return:
        """
        self.cluster_key = self.__init_cluster_name()
        result_instance_list = []
        instances_list = self.__get_instances_data()
        if instances_list:
            for instance in instances_list:
                for item in instance:
                    instance_id = item['InstanceId']
                    if item.get('Tags'):
                        for tag in item['Tags']:
                            if self.cluster_key:
                                if tag['Key'] == self.cluster_key:
                                    if self.input_tags:
                                        all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                        self.ec2_client.create_tags(Resources=[instance_id], Tags=all_tags)
                                    result_instance_list.append(instance_id)
                            else:
                                if self.cluster_prefix in tag['Key']:
                                    if self.input_tags:
                                        all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                        self.ec2_client.create_tags(Resources=[instance_id], Tags=all_tags)
                                    result_instance_list.append(instance_id)
        return sorted(result_instance_list)

    def cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        """
        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        volume_ids = self.__generate_cluster_resources_list_by_tag(resources_list=volumes_data, input_resource_id='VolumeId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[volume_ids], Tags=add_tags)
        return volume_ids

    def cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        ami_ids = self.__generate_cluster_resources_list_by_tag(resources_list=images_data, input_resource_id='ImageId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[ami_ids], Tags=add_tags)
        return ami_ids

    def cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        snapshot_ids = self.__generate_cluster_resources_list_by_tag(resources_list=snapshots_data,
                                                                     input_resource_id='SnapshotId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[snapshot_ids], Tags=add_tags)
        return snapshot_ids

    def __get_security_group_data(self):
        """
        This method return security group data
        :return:
        """
        security_groups = self.ec2_client.describe_security_groups()
        return security_groups['SecurityGroups']

    def cluster_security_group(self):
        """
        This method return list of cluster's security group according to cluster tag name
        :return:
        """
        security_group_ids = self.__generate_cluster_resources_list_by_tag(resources_list=self.__get_security_group_data(),
                                                                           input_resource_id='GroupId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[security_group_ids], Tags=add_tags)
        return security_group_ids

    def cluster_elastic_ip(self):
        """
        This method return list of cluster's elastic ip according to cluster tag name
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        elastic_ips = self.__generate_cluster_resources_list_by_tag(resources_list=elastic_ips_data,
                                                                    input_resource_id='AllocationId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[elastic_ips], Tags=add_tags)
        return elastic_ips

    def cluster_network_interface(self):
        """
        This method return list of cluster's network interface according to cluster tag name
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()
        network_interfaces_data = network_interfaces['NetworkInterfaces']
        network_interface_ids = self.__generate_cluster_resources_list_by_tag(resources_list=network_interfaces_data,
                                                                              input_resource_id='NetworkInterfaceId',
                                                                              tags='TagSet')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[network_interface_ids], Tags=add_tags)
        return network_interface_ids

    def cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        """
        result_resources_list = []
        response = ''
        load_balancers = self.elb_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancerDescriptions']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerName']
            tags = self.elb_client.describe_tags(LoadBalancerNames=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_key:
                            if tag['Key'] == self.cluster_key:
                                if self.input_tags:
                                    all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                    try:
                                        response = self.elb_client.add_tags(LoadBalancerNames=[resource_id], Tags=all_tags)
                                    except Exception as err:
                                        logger.exception(f'Tags are already updated, {err}')
                                result_resources_list.append(resource_id)
                        else:
                            if self.cluster_name in tag['Key']:
                                if self.input_tags:
                                    all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                    try:
                                        response = self.elb_client.add_tags(LoadBalancerNames=[resource_id], Tags=all_tags)
                                    except Exception as err:
                                        logger.exception(f'Tags are already updated, {err}')
                                result_resources_list.append(resource_id)
        return sorted(result_resources_list)

    def cluster_load_balancer_v2(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        """
        result_resources_list = []
        load_balancers = self.elbv2_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancers']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerArn']
            tags = self.elbv2_client.describe_tags(ResourceArns=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_key:
                            if tag['Key'] == self.cluster_key:
                                if self.input_tags:
                                    all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                    try:
                                        self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                    except Exception as err:
                                        logger.exception(f'Tags are already updated, {err}')
                                result_resources_list.append(resource_id)
                        else:
                            if self.cluster_name in tag['Key']:
                                if self.input_tags:
                                    all_tags = self.__append_input_tags(current_tags=item['Tags'])
                                    try:
                                        self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                    except Exception as err:
                                        logger.exception(f'Tags are already updated, {err}')
                                result_resources_list.append(resource_id)
        return sorted(result_resources_list)

    def cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        vpc_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpcs_data,
                                                                input_resource_id='VpcId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[vpc_ids], Tags=add_tags)
        return vpc_ids

    def cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        subnet_ids = self.__generate_cluster_resources_list_by_tag(resources_list=subnets_data,
                                                                   input_resource_id='SubnetId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[subnet_ids], Tags=add_tags)
        return subnet_ids

    def cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        route_table_ids = self.__generate_cluster_resources_list_by_tag(resources_list=route_tables_data,
                                                                        input_resource_id='RouteTableId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[route_table_ids], Tags=add_tags)
        return route_table_ids

    def cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        internet_gateway_ids = self.__generate_cluster_resources_list_by_tag(resources_list=internet_gateways_data,
                                                                             input_resource_id='InternetGatewayId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[internet_gateway_ids], Tags=add_tags)
        return internet_gateway_ids

    def cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        dhcp_ids = self.__generate_cluster_resources_list_by_tag(resources_list=dhcp_options_data,
                                                                 input_resource_id='DhcpOptionsId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[dhcp_ids], Tags=add_tags)
        return dhcp_ids

    def cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        vpc_endpoint_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpc_endpoints_data,
                                                                         input_resource_id='VpcEndpointId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[vpc_endpoint_ids], Tags=add_tags)
        return vpc_endpoint_ids

    def cluster_nat_gateway(self):
        """
        This method return list of cluster's nat gateway according to cluster tag name
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        nat_gateway_id = self.__generate_cluster_resources_list_by_tag(resources_list=nat_gateways_data,
                                                                       input_resource_id='NatGatewayId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[nat_gateway_id], Tags=add_tags)
        return nat_gateway_id

    def cluster_network_acl(self):
        """
        This method return list of cluster's network acl according to cluster vpc id
        Missing OpenShift Tags for it based on VPCs
        """
        network_acls = self.ec2_client.describe_network_acls()
        network_acls_data = network_acls['NetworkAcls']
        network_acl_ids = self.__generate_cluster_resources_list_by_vpc(resources_list=network_acls_data,
                                                                        input_resource_id='NetworkAclId')
        if self.input_tags:
            add_tags = self.__append_input_tags()
            self.ec2_client.create_tags(Resources=[network_acl_ids], Tags=add_tags)
        return network_acl_ids

    def cluster_role(self):
        """
        This method return list of cluster's role according to cluster name
        """
        # tag_role
        result_role_list = []
        # if cluster_key exit
        if self.cluster_key:
            # starts with cluster name, search for specific role name for fast scan (a lot of roles)
            role_name_list = [f"{self.cluster_key.replace(self.cluster_prefix, '')}-master-role", f"{self.cluster_key.replace(self.cluster_prefix, '')}-worker-role"]

            for role_name in role_name_list:
                try:
                    role = self.iam_client.get_role(RoleName=role_name)
                    role_data = role['Role']
                    result_role_list.append(role_data['Arn'])
                    if self.input_tags:
                        all_tags = self.__append_input_tags(current_tags=role_data['Tags'])
                        try:
                            self.iam_client.tag_role(RoleName=role_name, Tags=all_tags)
                        except Exception as err:
                            logger.exception(f'Tags are already updated, {err}')

                except Exception as err:
                    logger.exception(f'Missing cluster role name: {role_name}, {err}')

        return sorted(result_role_list)

    def cluster_user(self):
        """
        This method return list of cluster's user according to cluster name
        """
        # tag_user
        result_user_list = []
        users = self.iam_client.list_users()
        users_data = users['Users']
        # return self.__generate_cluster_resources_list_by_tag(resources_list=users_data,
        #                                                      input_resource_id='UserId')
        for user in users_data:
            user_name = user['UserName']
            user_data = self.iam_client.get_user(UserName=user_name)
            data = user_data['User']
            user_id = data['UserId']
            if data.get('Tags'):
                for tag in data['Tags']:
                    if tag['Key'] == self.cluster_key:
                        if self.input_tags:
                            all_tags = self.__append_input_tags(current_tags=data['Tags'])
                            self.iam_client.tag_user(UserName=user_name, Tags=all_tags)
                        result_user_list.append(user_id)
        return sorted(result_user_list)

    def cluster_s3_bucket(self):
        """
        This method return list of cluster's s3 bucket according to cluster name
        """
        bucket_result_list = []
        response = self.s3_client.list_buckets()
        # if cluster_key exit
        if self.cluster_key:
            for bucket in response['Buckets']:
                # starts with cluster name
                if bucket['Name'].startswith(self.cluster_key.replace(self.cluster_name, '')):
                    if self.input_tags:
                        add_tags = self.__append_input_tags()
                        # self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                    bucket_result_list.append(bucket['Name'])
        else:
            for bucket in response['Buckets']:
                # fast filter
                try:
                    tags = self.s3_client.get_bucket_tagging(Bucket=bucket['Name'])
                except Exception as e:  # continue when no bucket tags
                    continue
                for tag in tags['TagSet']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        if self.input_tags:
                            add_tags = self.__append_input_tags()
                            # self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                        bucket_result_list.append(bucket.get('Name'))

        return sorted(bucket_result_list)
