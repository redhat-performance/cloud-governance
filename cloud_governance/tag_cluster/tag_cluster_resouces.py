import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.iam.iam_operations import IAMOperatons
from cloud_governance.common.aws.utils.utils import Utils
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

    def __init__(self, cluster_name: str = None, cluster_prefix: str = None, input_tags: dict = None,
                 region: str = 'us-east-2', dry_run: str = 'yes'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.iam_operations = IAMOperatons()
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.cluster_key = self.__init_cluster_name()
        self.input_tags = input_tags
        self.__get_details_resource_list = Utils().get_details_resource_list
        self.__get_username_from_instance_id_and_time = CloudTrailOperations(region_name=region).get_username_by_instance_id_and_time
        self.dry_run = dry_run

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

    def __check_name_in_tags(self, tags: list, resource_id: str):
        found = False
        cluster_name = self.cluster_name
        for tag in tags:
            if tag.get('Key') == 'Name':
                found = True
                break
        for tag in tags:
            if self.cluster_prefix in tag.get('Key'):
                cluster_name = tag['Key']
                break
        if not found:
            value = cluster_name.split('/')[-1]+'-'+resource_id.split('-')[0]+'-'+resource_id[-4:]
            tags.append({'Key': 'Name', 'Value': value})
        return tags

    def __get_cluster_tags_by_instance_cluster(self, cluster_name: str):
        instances_list = self.__get_instances_data()
        if instances_list:
            for instance in instances_list:
                for item in instance:
                    if item.get('Tags'):
                        for tag in item.get('Tags'):
                            if self.cluster_prefix in tag.get('Key'):
                                if tag.get('Key') == cluster_name:
                                    i_tags = [instance_tag for instance_tag in item.get('Tags') if instance_tag.get('Key') != 'Name']
                                    return [i_tag for i_tag in i_tags if i_tag.get('Key') != cluster_name]
        return []

    def __generate_cluster_resources_list_by_tag(self, resources_list: list, input_resource_id: str,
                                                 tags: str = 'Tags'):
        """
        This method return resource list that related to input resource id according to cluster's tag name
        """
        result_resources_list = []
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get(tags):
                for tag in resource[tags]:
                    if self.cluster_prefix in tag.get('Key'):
                        add_tags = self.__append_input_tags(resource.get(tags))
                        instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                        add_tags.extend(instance_tags)
                        add_tags = self.__check_name_in_tags(tags=add_tags, resource_id=resource_id)
                        add_tags = self.__filter_resource_tags_by_add_tags(resource.get(tags), add_tags)
                        if add_tags:
                            if self.dry_run == "no":
                                cluster_resource_name = tag.get('Key').split('/')[-1]
                                if cluster_resource_name == self.cluster_name:
                                    self.ec2_client.create_tags(Resources=[resource_id], Tags=add_tags)
                                else:
                                    self.ec2_client.create_tags(Resources=[resource_id], Tags=add_tags)
                                logger.info(add_tags)
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
        cluster_instances = {}
        result_instance_list = []
        cluster_names = set()
        cluster_tags = {}
        instances_list = self.__get_instances_data()
        if instances_list:
            for instance in instances_list:
                for item in instance:
                    instance_id = item['InstanceId']
                    if item.get('Tags'):
                        for tag in item['Tags']:
                            if self.cluster_prefix in tag.get('Key'):
                                add_tags = self.__append_input_tags()
                                cluster_name = tag.get('Key').split('/')[-1]
                                if cluster_name in cluster_instances:
                                    cluster_instances[cluster_name].append(instance_id)
                                    break
                                else:
                                    cluster_instances[cluster_name] = [instance_id]
                                    username = self.__get_username_from_instance_id_and_time(start_time=item.get('LaunchTime'), resource_id=instance_id, resource_type='AWS::EC2::Instance')
                                    if username:
                                        user_tags = self.iam_operations.get_user_tags(username=username)
                                        add_tags.extend(user_tags)
                                    cluster_tags[cluster_name] = add_tags
                                    break
            for cluster_instance_name, instance_ids in cluster_instances.items():
                if self.dry_run == "no":
                    if cluster_instance_name == self.cluster_name:
                        self.ec2_client.create_tags(Resources=instance_ids, Tags=cluster_tags.get(cluster_instance_name))
                    else:
                        self.ec2_client.create_tags(Resources=instance_ids,
                                                    Tags=cluster_tags.get(cluster_instance_name))
                    logger.info(cluster_tags.get(cluster_instance_name))
                result_instance_list.extend(instance_ids)
                cluster_names.add(cluster_instance_name)
        if not self.cluster_key:
            s3_buckets = []
            role_ids = []
            usernames = []
            # for cluster_name in cluster_names:
            #     roles = self.cluster_role(cluster_name=cluster_name)
            #     role_ids.extend(roles)
            #     s3_tagging = self.cluster_s3_bucket(cluster_name=cluster_name)
            #     s3_buckets.extend(s3_tagging)
            #     username = self.cluster_user(cluster_name=cluster_name)
            #     usernames.extend(username)
            # logger.info(f'cluster_roles count: {len(role_ids)}, {role_ids}')
            # logger.info(f'cluster_user count: {len(usernames)}, {usernames}')
            # logger.info(f'cluster_s3_bucket count: {len(s3_buckets)}, {s3_buckets}')
        return sorted(result_instance_list)

    def cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        """
        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        volume_ids = self.__generate_cluster_resources_list_by_tag(resources_list=volumes_data,
                                                                   input_resource_id='VolumeId')
        return volume_ids

    def cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        ami_ids = self.__generate_cluster_resources_list_by_tag(resources_list=images_data, input_resource_id='ImageId')
        return ami_ids

    def cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        snapshot_ids = self.__generate_cluster_resources_list_by_tag(resources_list=snapshots_data,
                                                                     input_resource_id='SnapshotId')
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
        security_group_ids = self.__generate_cluster_resources_list_by_tag(
            resources_list=self.__get_security_group_data(),
            input_resource_id='GroupId')

        return security_group_ids

    def cluster_elastic_ip(self):
        """
        This method return list of cluster's elastic ip according to cluster tag name
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        elastic_ips = self.__generate_cluster_resources_list_by_tag(resources_list=elastic_ips_data,
                                                                    input_resource_id='AllocationId')
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
                        all_tags = self.__append_input_tags(current_tags=item['Tags'])
                        all_tags = self.__filter_resource_tags_by_add_tags(item.get('Tags'), all_tags)
                        if all_tags:
                            if self.cluster_key:
                                if tag['Key'] == self.cluster_key:
                                    if self.dry_run == 'no':
                                        try:
                                            response = self.elb_client.add_tags(LoadBalancerNames=[resource_id],
                                                                                Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
                            else:
                                if self.cluster_name in tag['Key']:
                                    if self.dry_run == 'no':
                                        try:
                                            response = self.elb_client.add_tags(LoadBalancerNames=[resource_id],
                                                                                Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
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
                        all_tags = self.__append_input_tags(current_tags=item['Tags'])
                        all_tags = self.__filter_resource_tags_by_add_tags(item.get('Tags'), all_tags)
                        if all_tags:
                            if self.cluster_key:
                                if tag['Key'] == self.cluster_key:
                                    if self.dry_run == 'no':
                                        try:
                                            self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
                            else:
                                if self.cluster_name in tag['Key']:
                                    if self.dry_run == 'no':
                                        try:
                                            self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
        return sorted(result_resources_list)

    def cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        vpc_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpcs_data,
                                                                input_resource_id='VpcId')
        return vpc_ids

    def cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        subnet_ids = self.__generate_cluster_resources_list_by_tag(resources_list=subnets_data,
                                                                   input_resource_id='SubnetId')
        return subnet_ids

    def cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        route_table_ids = self.__generate_cluster_resources_list_by_tag(resources_list=route_tables_data,
                                                                        input_resource_id='RouteTableId')
        return route_table_ids

    def cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        internet_gateway_ids = self.__generate_cluster_resources_list_by_tag(resources_list=internet_gateways_data,
                                                                             input_resource_id='InternetGatewayId')
        return internet_gateway_ids

    def cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        dhcp_ids = self.__generate_cluster_resources_list_by_tag(resources_list=dhcp_options_data,
                                                                 input_resource_id='DhcpOptionsId')
        return dhcp_ids

    def cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        vpc_endpoint_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpc_endpoints_data,
                                                                         input_resource_id='VpcEndpointId')
        return vpc_endpoint_ids

    def cluster_nat_gateway(self):
        """
        This method return list of cluster's nat gateway according to cluster tag name
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        nat_gateway_id = self.__generate_cluster_resources_list_by_tag(resources_list=nat_gateways_data,
                                                                       input_resource_id='NatGatewayId')
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
        return network_acl_ids

    def cluster_role(self, cluster_name: str = ''):
        """
        This method return list of cluster's role according to cluster name
        """
        # tag_role
        result_role_list = []
        # if cluster_key exit
        cluster_key = self.cluster_name if self.cluster_key else cluster_name
        if cluster_key:
            # starts with cluster name, search for specific role name for fast scan (a lot of roles)
            role_name_list = [f"{cluster_key}-master-role", f"{cluster_key}-worker-role"]

            for role_name in role_name_list:
                try:
                    role = self.iam_client.get_role(RoleName=role_name)
                    role_data = role['Role']
                    all_tags = self.__append_input_tags(current_tags=role_data['Tags'])
                    all_tags = self.__filter_resource_tags_by_add_tags(role_data.get('Tags'), all_tags)
                    if all_tags:
                        if self.dry_run == 'no':
                            try:
                                self.iam_client.tag_role(RoleName=role_name, Tags=all_tags)
                                logger.info(all_tags)
                            except Exception as err:
                                logger.exception(f'Tags are already updated, {err}')
                        result_role_list.append(role_data['Arn'])
                except Exception as err:
                    logger.exception(f'Missing cluster role name: {role_name}, {err}')

        return sorted(result_role_list)

    def cluster_user(self, cluster_name: str = ''):
        """
        This method return list of cluster's user according to cluster name
        """
        # tag_user
        result_user_list = []
        users = self.__get_details_resource_list(self.iam_client.list_users, input_tag='Users',
                                                 check_tag='Marker')
        # return self.__generate_cluster_resources_list_by_tag(resources_list=users_data,
        #                                                      input_resource_id='UserId')
        cluster_name = self.cluster_name if self.cluster_key else cluster_name
        for user in users:
            user_name = user['UserName']
            if cluster_name in user_name:
                user_data = self.iam_client.get_user(UserName=user_name)
                data = user_data['User']
                if data.get('Tags'):
                    for tag in data['Tags']:
                        if cluster_name in tag['Key']:
                            all_tags = self.__append_input_tags(current_tags=data['Tags'])
                            all_tags = self.__filter_resource_tags_by_add_tags(data.get('Tags'), all_tags)
                            if all_tags:
                                if self.dry_run == 'no':
                                    self.iam_client.tag_user(UserName=user_name, Tags=all_tags)
                                    logger.info(all_tags)
                                result_user_list.append(user_name)
                            break
        return sorted(result_user_list)

    def __filter_resource_tags_by_add_tags(self, tags: list, search_tags: list):
        """
        This method filters the bucket tags
        @param tags:
        @param search_tags:
        @return:
        """
        add_tags = []
        if tags:
            for search_tag in search_tags:
                found = False
                for tag in tags:
                    if tag.get('Key') == search_tag.get('Key'):
                        found = True
                if not found:
                    add_tags.append(search_tag)
        else:
            add_tags.extend(search_tags)
        return add_tags

    def cluster_s3_bucket(self, cluster_name: str = ''):
        """
        This method return list of cluster's s3 bucket according to cluster name
        """
        bucket_result_list = []
        response = self.s3_client.list_buckets()
        # if cluster_key exit
        cluster_key = self.cluster_name if self.cluster_key else cluster_name
        if cluster_key:
            for bucket in response['Buckets']:
                # starts with cluster name
                if bucket['Name'].startswith(cluster_key):
                    bucket_tags = self.s3_client.get_bucket_tagging(Bucket=bucket.get('Name'))
                    if bucket_tags:
                        bucket_tags = bucket_tags['TagSet']
                        add_tags = self.__append_input_tags(bucket_tags)
                        add_tags = self.__filter_resource_tags_by_add_tags(bucket_tags, add_tags)
                        if add_tags:
                            if self.dry_run == 'no':
                                self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                                logger.info(add_tags)
                            bucket_result_list.append(bucket['Name'])

        return sorted(bucket_result_list)
