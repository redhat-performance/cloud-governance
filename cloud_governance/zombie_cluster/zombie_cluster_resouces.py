import boto3
from cloud_governance.common.logger.init_logger import logger


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

    def __init__(self, cluster_prefix: str = None, delete: bool = False, region: str = 'us-east-2'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.cluster_prefix = cluster_prefix
        self.delete = delete

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
                        result_resources_key_id[resource_id] = tag['Key']
        return result_resources_key_id

    def __get_zombie_resources(self, exist_resources: dict):
        """
        This method filter zombie resource, meaning no active instance for this cluster
        """
        zombie_resources = []
        zombies_values = set(exist_resources.values()) - set(self._cluster_instance().values())

        for zombie_value in zombies_values:
            for key, value in exist_resources.items():
                if zombie_value == value:
                    zombie_resources.append(key)
        return sorted(zombie_resources)

    def __get_all_zombie_resources(self, exist_resources: dict):
        """
        This method filter zombie resource, meaning no active instance for this cluster in all regions
        """
        zombie_resources = []
        zombies_values = set(exist_resources.values()) - set(self._all_cluster_instance().values())

        for zombie_value in zombies_values:
            for key, value in exist_resources.items():
                if zombie_value == value:
                    zombie_resources.append(key)
        return sorted(zombie_resources)

    def zombie_cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name,
        delete only available resource that related to cluster
        """
        available_volumes = []
        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        # filter in-use resource
        for volume in volumes_data:
            if volume['State'] == 'available':
                available_volumes.append(volume)
        exist_volume = self.__get_cluster_resources(resources_list=available_volumes, input_resource_id='VolumeId')
        zombies = self.__get_zombie_resources(exist_volume)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_volume(VolumeId=zombie)
                    logger.info(f'delete_volume: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_volume: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
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
        return sorted(zombies)

    def zombie_cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        exist_snapshot = self.__get_cluster_resources(resources_list=snapshots_data,
                                                             input_resource_id='SnapshotId')
        zombies = self.__get_zombie_resources(exist_snapshot)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_snapshot(SnapshotId=zombie)
                    logger.info(f'delete_snapshot: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_snapshot: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_security_group(self):
        """
        This method return list of zombie cluster's security groups compare to existing instances
        :return: list of zombie cluster's security groups
        """
        security_groups = self.ec2_client.describe_security_groups()
        exist_security_group = self.__get_cluster_resources(resources_list=security_groups['SecurityGroups'],
                                            input_resource_id='GroupId')
        zombies = self.__get_zombie_resources(exist_security_group)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_security_group(GroupId=zombie)
                    logger.info(f'delete_security_group: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_security_group: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_elastic_ip(self):
        """
        This method return list of zombie cluster's elastic ip according to existing instances
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        exist_elastic_ip = self.__get_cluster_resources(resources_list=elastic_ips_data,
                                                             input_resource_id='AssociationId')
        zombies = self.__get_zombie_resources(exist_elastic_ip)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.disassociate_address(AssociationId=zombie)
                    logger.info(f'disassociate_address: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot disassociate_address: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_network_interface(self):
        """
        This method return list of zombie cluster's network interface according to existing instances
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()
        network_interfaces_data = network_interfaces['NetworkInterfaces']
        exist_network_interface = self.__get_cluster_resources(resources_list=network_interfaces_data,
                                                             input_resource_id='NetworkInterfaceId',
                                                             tags='TagSet')
        zombies = self.__get_zombie_resources(exist_network_interface)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_network_interface(NetworkInterfaceId=zombie)
                    logger.info(f'delete_network_interface: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot disassociate_address: {zombie}, {err}')
        return sorted(zombies)

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
        zombies = self.__get_zombie_resources(exist_load_balancer)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_load_balancer(LoadBalancerName=zombie)
                    logger.info(f'delete_load_balancer: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_load_balancer: {zombie}, {err}')
        return sorted(zombies)

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
        zombies = self.__get_zombie_resources(exist_load_balancer)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_load_balancer(LoadBalancerArn=zombie)
                    logger.info(f'delete_load_balancer: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_load_balancer: {zombie}, {err}')
        return sorted(zombies)

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
        zombies = self.__get_zombie_resources(exist_vpc)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_vpc(VpcId=zombie)
                    logger.info(f'delete_vpc: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_vpc: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        exist_subnet = self.__get_cluster_resources(resources_list=subnets_data,
                                                             input_resource_id='SubnetId')
        zombies = self.__get_zombie_resources(exist_subnet)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_subnet(SubnetId=zombie)
                    logger.info(f'delete_subnet: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_subnet: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        exist_route_table = self.__get_cluster_resources(resources_list=route_tables_data,
                                                             input_resource_id='RouteTableId')
        zombies = self.__get_zombie_resources(exist_route_table)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_route_table(RouteTableId=zombie)
                    logger.info(f'delete_route_table: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_route_table: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        exist_internet_gateway = self.__get_cluster_resources(resources_list=internet_gateways_data,
                                                             input_resource_id='InternetGatewayId')
        zombies = self.__get_zombie_resources(exist_internet_gateway)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_internet_gateway(InternetGatewayId=zombie)
                    logger.info(f'delete_internet_gateway: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_internet_gateway: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        exist_dhcp_option = self.__get_cluster_resources(resources_list=dhcp_options_data,
                                                             input_resource_id='DhcpOptionsId')
        zombies = self.__get_zombie_resources(exist_dhcp_option)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_dhcp_options(DhcpOptionsId=zombie)
                    logger.info(f'delete_internet_gateway: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_internet_gateway: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        exist_vpc_endpoint = self.__get_cluster_resources(resources_list=vpc_endpoints_data,
                                                             input_resource_id='VpcEndpointId')
        zombies = self.__get_zombie_resources(exist_vpc_endpoint)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_vpc_endpoints(VpcEndpointIds=[zombie])
                    logger.info(f'delete_vpc_endpoints: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_vpc_endpoints: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_nat_gateway(self):
        """
        This method return list of zombie cluster's nat gateway according to cluster tag name
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        exist_nat_gateway = self.__get_cluster_resources(resources_list=nat_gateways_data,
                                                             input_resource_id='NatGatewayId')
        zombies = self.__get_zombie_resources(exist_nat_gateway)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_nat_gateway(NatGatewayId=zombie)
                    logger.info(f'delete_nat_gateway: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_nat_gateway: {zombie}, {err}')
        return sorted(zombies)

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
        zombies = zombie_resources
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    self.ec2_client.delete_network_acl(NetworkAclId=zombie)
                    logger.info(f'delete_network_acl: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_network_acl: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_role(self):
        """
        This method return list of cluster's role in all regions according to cluster name
        * Role is a global resource, need to scan for live cluster in all regions
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
        zombies = self.__get_all_zombie_resources(exist_role_name_tag)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    # Detach policy from role
                    self.iam_client.delete_role_policy(RoleName=zombie, PolicyName=zombie.replace('role', 'policy'))
                    self.iam_client.remove_role_from_instance_profile(RoleName=zombie, InstanceProfileName=zombie.replace('role', 'profile'))
                    self.iam_client.delete_role(RoleName=zombie)
                    logger.info(f'delete_role: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_role: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_user(self):
        """
        This method return list of cluster's user according to cluster name
        * User is a global resource, need to scan for live cluster in all regions
        """
        exist_user_name_tag = {}
        users = self.iam_client.list_users()
        users_data = users['Users']
        for user in users_data:
            user_name = user['UserName']
            user_data = self.iam_client.get_user(UserName=user_name)
            data = user_data['User']
            if data.get('Tags'):
                for tag in data['Tags']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        exist_user_name_tag[user_name] = tag['Key']
        zombies = self.__get_all_zombie_resources(exist_user_name_tag)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    # Detach policy from user
                    user_policies = self.iam_client.list_user_policies(UserName=zombie)
                    if user_policies['PolicyNames']:
                        self.iam_client.delete_user_policy(UserName=zombie, PolicyName=f'{zombie}-policy')
                    list_access_key = self.iam_client.list_access_keys(UserName=zombie)
                    # delete user access key
                    for access_key in list_access_key['AccessKeyMetadata']:
                        self.iam_client.delete_access_key(UserName=zombie, AccessKeyId=access_key['AccessKeyId'])
                    self.iam_client.delete_user(UserName=zombie)
                    logger.info(f'delete_user: {zombie}')
                except Exception as err:
                     logger.exception(f'Cannot delete_user: {zombie}, {err}')
        return sorted(zombies)

    def zombie_cluster_s3_bucket(self, cluster_stamp: str = 'image-registry'):
        """
        This method return list of cluster's s3 bucket according to cluster name
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
                except Exception:  # continue when no bucket tags
                    continue
                for tag in tags['TagSet']:
                    if tag['Key'].startswith(self.cluster_prefix):
                        exist_bucket_name_tag[bucket['Name']] = tag['Key']
        zombies = self.__get_all_zombie_resources(exist_bucket_name_tag)
        if zombies and self.delete:
            for zombie in zombies:
                try:
                    # delete bucket objects
                    bucket = self.s3_resource.Bucket(zombie)
                    bucket.objects.all().delete()
                    # delete bucket
                    self.s3_client.delete_bucket(Bucket=zombie)
                    logger.info(f'delete_bucket: {zombie}')
                except Exception as err:
                    logger.exception(f'Cannot delete_bucket: {zombie}, {err}')
        return sorted(zombies)

# zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=False, region='us-east-2')
# print(zombie_cluster_resources.zombie_cluster_subnet())