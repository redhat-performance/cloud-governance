from datetime import datetime
from multiprocessing import Process, Queue

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class RemoveClusterTags:
    """
    This class removes the tags of cluster resources
    """

    def __init__(self, input_tags: dict, cluster_name: str = None, cluster_prefix: str = None,
                 region: str = 'us-east-2'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.iam_operations = IAMOperations()
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.input_tags = input_tags
        self.__get_details_resource_list = Utils().get_details_resource_list
        self.__get_username_from_instance_id_and_time = CloudTrailOperations(
            region_name=region).get_username_by_instance_id_and_time
        self.ec2_operations = EC2Operations()

    def __get_instances_data(self):
        """
        This method go over all instances
        @return:
        """
        instances_list = []
        ec2s_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_instances,
                                                     input_tag='Reservations', check_tag='NextToken')
        for items in ec2s_data:
            if items.get('Instances'):
                instances_list.append(items['Instances'])
        return instances_list

    def __input_tags_list_builder(self):
        """
        This method build tags list according to input tags dictionary
        @return:
        """
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def get_tags(self, tags: list):
        """
        This filters and return key:value pairs of values
        @param tags:
        @return:
        """
        tags_list = {}
        for tag in tags:
            key = tag.get('Key')
            value = tag.get('Value')
            tags_list[key] = value
        return tags_list

    def remove_instance_tags(self, instance_list: list, tags: list):
        """
        This method removes tags from instances
        @param instance_list:
        @param tags:
        @return:
        """
        tags_dict = self.get_tags(tags)
        username = tags_dict.get('Username')
        if not username:
            username = self.__get_username_from_instance_id_and_time(
                start_time=datetime.strptime(tags_dict.get('LaunchTime'), '%Y-%m-%d %H:%M:%S+00:00'),
                resource_id=instance_list[0],
                resource_type='AWS::EC2::Instance')
        added_tags = self.iam_operations.get_user_tags(username=username)
        added_tags.append({'Key': 'LaunchTime', 'Value': tags_dict.get('LaunchTime')})
        added_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
        added_tags.extend(self.__input_tags_list_builder())
        if 'email' in tags:
            added_tags.append({'email': 'LaunchTime', 'Value': f'{username}@redhat.com'})
        self.ec2_client.delete_tags(Resources=instance_list, Tags=added_tags)
        logger.info(f'InstanceId :: {instance_list} {added_tags}')
        return added_tags

    def get_cluster(self, clusters: list):
        """
        This method return cluster, and it tags
        @param clusters:
        @return:
        """
        cluster_dict = {}
        cluster_tags = {}
        for instance in clusters:
            for item in instance:
                if item.get('Tags'):
                    for tag in item.get('Tags'):
                        key = tag.get('Key')
                        if self.cluster_prefix in key:
                            if self.cluster_name:
                                if f'{self.cluster_prefix}{self.cluster_name}' == key:
                                    if key in cluster_dict:
                                        cluster_dict[key].append(item.get('InstanceId'))
                                    else:
                                        cluster_dict[key] = [item.get('InstanceId')]
                                        cluster_tags[key] = item.get('Tags')
                                    break
                            else:
                                if key in cluster_dict:
                                    cluster_dict[key].append(item.get('InstanceId'))
                                else:
                                    cluster_dict[key] = [item.get('InstanceId')]
                                    cluster_tags[key] = item.get('Tags')
                                break
        return [cluster_dict, cluster_tags]

    def cluster_instance(self):
        """
        This method removes the tags of cluster and non-cluster
        @return:
        """
        instance_list = self.__get_instances_data()
        cluster, non_cluster = self.ec2_operations.scan_cluster_or_non_cluster_instance(instance_list)
        cluster_list, cluster_tags = self.get_cluster(cluster)
        result = {}
        for cluster_name, cluster_ids in cluster_list.items():
            added_tags = (self.remove_instance_tags(cluster_ids, cluster_tags.get(cluster_name)))
            result[cluster_name] = added_tags
        return result

    def remove_tags_of_resources(self, resource_list: list, instance_tags: dict, resource_id: str, tags: str = 'Tags'):
        """
        This method removes the tags or resources like Volume, Snapshots, Vpc, Subnets
        @param resource_list:
        @param instance_tags:
        @param resource_id:
        @param tags:
        @return:
        """
        cluster_resources = {}
        for resource in resource_list:
            if resource.get(tags):
                for tag in resource.get(tags):
                    if self.cluster_prefix in tag.get('Key'):
                        if self.cluster_name:
                            if f'{self.cluster_prefix}{self.cluster_name}' == tag.get('Key'):
                                if resource.get('CreateTime'):
                                    instance_tags[tag.get('Key')].append(
                                        {'Key': 'CreateTime', 'Value': str(resource.get('CreateTime'))})
                                if resource.get('StartTime'):
                                    instance_tags[tag.get('Key')].append(
                                        {'Key': 'StartTime', 'Value': str(resource.get('StartTime'))})
                                if tag.get('Key') in cluster_resources:
                                    cluster_resources[tag.get('Key')].append(resource.get(resource_id))
                                else:
                                    cluster_resources[tag.get('Key')] = [resource.get(resource_id)]
                        else:
                            if resource.get('CreateTime'):
                                instance_tags[tag.get('Key')].append(
                                    {'Key': 'CreateTime', 'Value': str(resource.get('CreateTime'))})
                            if resource.get('StartTime'):
                                instance_tags[tag.get('Key')].append(
                                    {'Key': 'StartTime', 'Value': str(resource.get('StartTime'))})
                            if tag.get('Key') in cluster_resources:
                                cluster_resources[tag.get('Key')].append(resource.get(resource_id))
                            else:
                                cluster_resources[tag.get('Key')] = [resource.get(resource_id)]
        for cluster_name, resource_ids in cluster_resources.items():
            self.ec2_client.delete_tags(Resources=resource_ids, Tags=instance_tags.get(cluster_name))
            logger.info(f'{resource_id} :: {resource_ids} {instance_tags.get(cluster_name)}')

    def cluster_volume(self, instance_tags: dict):
        """
        This method filters the cluster and non-cluster and removes it tags
        @param instance_tags:
        @return:
        """
        volumes_data = self.__get_details_resource_list(func_name=self.ec2_client.describe_volumes, input_tag='Volumes',
                                                        check_tag='NextToken')
        cluster_volume, non_cluster_volume = self.ec2_operations.scan_cluster_non_cluster_resources(volumes_data)
        self.remove_tags_of_resources(cluster_volume, instance_tags, 'VolumeId')
        return len(cluster_volume)

    def cluster_images(self, instance_tags: dict):
        """
        This method rmoves the tags of cluster and non-cluster images
        @param instance_tags:
        @return:
        """
        images_data = self.ec2_client.describe_images(Owners=['self'])['Images']
        cluster_images, non_cluster_ = self.ec2_operations.scan_cluster_non_cluster_resources(images_data)
        self.remove_tags_of_resources(cluster_images, instance_tags, 'ImageId')
        return len(cluster_images)

    def cluster_snapshot(self, instance_tags: dict):
        """
        This method return list of cluster's snapshot according to cluster tag name
        @return:
        """
        snapshots_data = self.ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
        cluster_snapshot, non_cluster_snapshot = self.ec2_operations.scan_cluster_non_cluster_resources(snapshots_data)
        self.remove_tags_of_resources(cluster_snapshot, instance_tags, 'SnapshotId')
        return len(cluster_snapshot)

    def generate_tag_key(self, tags: list):
        """
        This method returns keys from the resource tags
        @param tags:
        @return:
        """
        keys = []
        for tag in tags:
            keys.append({'Key': tag.get('Key')})
        return keys

    def cluster_load_balancer(self, instance_tags: dict):
        """
        This method remove tags  of cluster's load balancer
        @return:
        """
        cluster_resources = {}
        load_balancers_data = self.elb_client.describe_load_balancers()['LoadBalancerDescriptions']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerName']
            tags = self.elb_client.describe_tags(LoadBalancerNames=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_prefix in tag.get('Key'):
                            if self.cluster_name:
                                if f'{self.cluster_prefix}{self.cluster_name}' == tag.get('Key'):
                                    if item.get('CreatedTime'):
                                        instance_tags[tag.get('Key')].append(
                                            {'Key': 'CreatedTime', 'Value': str(item.get('CreatedTime'))})
                                    if tag.get('Key') in cluster_resources:
                                        cluster_resources[tag.get('Key')].append(resource.get('LoadBalancerName'))
                                    else:
                                        cluster_resources[tag.get('Key')] = [resource.get('LoadBalancerName')]
                            else:
                                if item.get('CreatedTime'):
                                    instance_tags[tag.get('Key')].append(
                                        {'Key': 'CreatedTime', 'Value': str(item.get('CreatedTime'))})
                                if tag.get('Key') in cluster_resources:
                                    cluster_resources[tag.get('Key')].append(resource.get('LoadBalancerName'))
                                else:
                                    cluster_resources[tag.get('Key')] = [resource.get('LoadBalancerName')]
        tags_remove_ids = []
        for cluster_name, cluster_ids in cluster_resources.items():
            for cluster_id in cluster_ids:
                self.elb_client.remove_tags(LoadBalancerNames=[cluster_id], Tags=self.generate_tag_key(instance_tags.get(cluster_name)))
            logger.info(f'LoadBalancerName :: {cluster_ids} {instance_tags.get(cluster_name)}')
            tags_remove_ids.extend(cluster_ids)
        return len(tags_remove_ids)

    def cluster_load_balancer_v2(self, instance_tags: dict):
        """
        This method removes the tags of cluster load balancers v2
        @return:
        """
        cluster_resources = {}
        load_balancers_data = self.elbv2_client.describe_load_balancers()['LoadBalancers']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerArn']
            tags = self.elbv2_client.describe_tags(ResourceArns=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_prefix in tag.get('Key'):
                            if self.cluster_name:
                                if f'{self.cluster_prefix}{self.cluster_name}' == tag.get('Key'):
                                    if item.get('CreatedTime'):
                                        instance_tags[tag.get('Key')].append(
                                            {'Key': 'CreatedTime', 'Value': str(item.get('CreatedTime'))})
                                    if tag.get('Key') in cluster_resources:
                                        cluster_resources[tag.get('Key')].append(resource_id)
                                    else:
                                        cluster_resources[tag.get('Key')] = [resource_id]
                            else:
                                if item.get('CreatedTime'):
                                    instance_tags[tag.get('Key')].append(
                                        {'Key': 'CreatedTime', 'Value': str(item.get('CreatedTime'))})
                                if tag.get('Key') in cluster_resources:
                                    cluster_resources[tag.get('Key')].append(resource_id)
                                else:
                                    cluster_resources[tag.get('Key')] = [resource_id]
        tags_remove_ids = []
        for cluster_name, cluster_ids in cluster_resources.items():
            for cluster_id in cluster_ids:
                self.elbv2_client.remove_tags(ResourceArns=[cluster_id], TagKeys=self.tag_keys(instance_tags.get(cluster_name)))
            logger.info(f'LoadBalancerArn :: {cluster_ids} {instance_tags.get(cluster_name)}')
            tags_remove_ids.extend(cluster_ids)
        return len(tags_remove_ids)

    def cluster_network_interface(self, instance_tags: dict):
        """
        This method removes the tags of cluster network_interfaces
        @return:
        """
        network_interfaces_data = self.__get_details_resource_list(
            func_name=self.ec2_client.describe_network_interfaces,
            input_tag='NetworkInterfaces', check_tag='NextToken')
        cluster_eni, non_cluster_eni = self.ec2_operations.scan_cluster_non_cluster_resources(network_interfaces_data,
                                                                                              tags='TagSet')
        self.remove_tags_of_resources(cluster_eni, instance_tags, 'NetworkInterfaceId', tags='TagSet')
        return len(cluster_eni)

    def cluster_elastic_ip(self, instance_tags: dict):
        """
        This method removes the tags of cluster elastic_ip
        @return:
        """
        elastic_ips_data = self.ec2_client.describe_addresses()['Addresses']
        cluster_eip, non_cluster_eip = self.ec2_operations.scan_cluster_non_cluster_resources(elastic_ips_data)
        self.remove_tags_of_resources(cluster_eip, instance_tags, 'AllocationId')
        return len(cluster_eip)

    def cluster_security_group(self, instance_tags: dict):
        """
        This method removes the tags of cluster security group
        @return:
        """
        security_groups_data = self.ec2_client.describe_security_groups()['SecurityGroups']
        cluster_sg, non_cluster_sg = self.ec2_operations.scan_cluster_non_cluster_resources(security_groups_data)
        self.remove_tags_of_resources(cluster_sg, instance_tags, 'GroupId')
        return len(cluster_sg)

    def cluster_vpc(self, instance_tags: dict):
        """
        This method removes the tags of cluster vpc
        @return:
        """
        vpcs_data = self.ec2_client.describe_vpcs()['Vpcs']
        cluster_vpc, non_cluster_vpc = self.ec2_operations.scan_cluster_non_cluster_resources(vpcs_data)
        self.remove_tags_of_resources(cluster_vpc, instance_tags, 'VpcId')
        return len(cluster_vpc)

    def cluster_subnet(self, instance_tags: dict):
        """
        This method removes the tags of cluster subnet
        @return:
        """
        subnets_data = self.ec2_client.describe_subnets()['Subnets']
        cluster_subnet, non_cluster_subnet = self.ec2_operations.scan_cluster_non_cluster_resources(subnets_data)
        self.remove_tags_of_resources(cluster_subnet, instance_tags, 'SubnetId')
        return len(cluster_subnet)

    def cluster_route_table(self, instance_tags: dict):
        """
        This method removes the tags of cluster route table
        @return:
        """
        route_tables_data = self.ec2_client.describe_route_tables()['RouteTables']
        cluster_rt, non_cluster_rt = self.ec2_operations.scan_cluster_non_cluster_resources(route_tables_data)
        self.remove_tags_of_resources(cluster_rt, instance_tags, 'RouteTableId')
        return len(cluster_rt)

    def cluster_internet_gateway(self, instance_tags: dict):
        """
        This method removes the tags of cluster internet gateway
        @return:
        """
        internet_gateways_data = self.ec2_client.describe_internet_gateways()['InternetGateways']
        cluster_ign, non_cluster_ign = self.ec2_operations.scan_cluster_non_cluster_resources(internet_gateways_data)
        self.remove_tags_of_resources(cluster_ign, instance_tags, 'InternetGatewayId')
        return len(cluster_ign)

    def cluster_dhcp_option(self, instance_tags: dict):
        """
        This method remove the tags of cluster dhcp
        @return:
        """
        dhcp_options_data = self.ec2_client.describe_dhcp_options()['DhcpOptions']
        cluster_dhcp, non_cluster_dhcp = self.ec2_operations.scan_cluster_non_cluster_resources(dhcp_options_data)
        self.remove_tags_of_resources(cluster_dhcp, instance_tags, 'DhcpOptionsId')
        return cluster_dhcp

    def cluster_vpc_endpoint(self, instance_tags: dict):
        """
        This method removes the tags of cluster vpc endpoints
        @return:
        """
        vpc_endpoints_data = self.ec2_client.describe_vpc_endpoints()['VpcEndpoints']
        cluster_vpce, non_cluster_vpce = self.ec2_operations.scan_cluster_non_cluster_resources(vpc_endpoints_data)
        self.remove_tags_of_resources(cluster_vpce, instance_tags, 'VpcEndpointId')
        return cluster_vpce

    def cluster_nat_gateway(self, instance_tags: dict):
        """
        This method removes the tags of cluster nat gateway
        @return:
        """
        nat_gateways_data = self.ec2_client.describe_nat_gateways()['NatGateways']
        cluster_ngw, non_cluster_ngw = self.ec2_operations.scan_cluster_non_cluster_resources(nat_gateways_data)
        self.remove_tags_of_resources(cluster_ngw, instance_tags, 'NatGatewayId')
        return cluster_ngw

    def cluster_network_acl(self, instance_tags: dict):
        """
        This method removes the cluster network acl by vpc
        Missing OpenShift Tags for it based on VPCs
        @return:
        """
        network_acls_data = self.ec2_client.describe_network_acls()['NetworkAcls']
        cluster_nacl, non_cluster_nacl = self.ec2_operations.scan_cluster_non_cluster_resources(network_acls_data)
        self.remove_tags_of_resources(cluster_nacl, instance_tags, 'NetworkAclId')
        return cluster_nacl

    def tag_keys(self, tags: list):
        """
        This method generate the keys
        @param tags:
        @return:
        """
        keys = []
        for tag in tags:
            keys.append(tag.get('Key'))
        return keys

    def cluster_role(self, instance_tags: dict):
        """
        This method removes the tags of cluster role
        @param instance_tags:
        @return:
        """
        cluster_names = [name.split('/')[-1] for name in instance_tags.keys()]
        cluster_ids = []
        for cluster_name in cluster_names:
            tags = []
            role_name_list = [f"{cluster_name}-master-role", f"{cluster_name}-worker-role"]
            for role_name in role_name_list:
                if self.cluster_name:
                    if self.cluster_name in role_name:
                        full_name = f'{self.cluster_prefix}{self.cluster_name}'
                        keys = self.tag_keys(list(instance_tags.get(full_name)))
                        keys.append('CreationDate')
                        self.iam_client.untag_role(RoleName=role_name, TagKeys=keys)
                        tags = list(instance_tags.get(full_name))
                else:
                    full_name = f'{self.cluster_prefix}{cluster_name}'
                    keys = self.tag_keys(list(instance_tags.get(full_name)))
                    keys.append('CreationDate')
                    self.iam_client.untag_role(RoleName=role_name, TagKeys=keys)
                    tags = list(instance_tags.get(full_name))
            logger.info(f'Role Name :: {role_name_list} {tags}')
            cluster_ids.extend(role_name_list)
        return cluster_ids

    def cluster_user(self, instance_tags: dict):
        """
        This method return list of cluster's user according to cluster name
        @param instance_tags:
        @return:
        """
        # tag_user
        cluster_names = [name.split('/')[-1] for name in instance_tags.keys()]
        user_ids = []
        for cluster_name in cluster_names:
            users = self.__get_details_resource_list(self.iam_client.list_users, input_tag='Users', check_tag='Marker')
            usernames = []
            tags = []
            for user in users:
                user_name = user['UserName']
                if cluster_name in user_name:
                    if self.cluster_name:
                        if self.cluster_name in user_name:
                            full_name = f'{self.cluster_prefix}{self.cluster_name}'
                            keys = self.tag_keys(instance_tags.get(full_name))
                            keys.append('CreationDate')
                            self.iam_client.untag_user(UserName=user_name, TagKeys=keys)
                            usernames.append(user_name)
                            tags = list(instance_tags.get(full_name))
                    else:
                        full_name = f'{self.cluster_prefix}{cluster_name}'
                        self.iam_client.untag_user(UserName=user_name, TagKeys=self.tag_keys(list(instance_tags.get(full_name))))
                        usernames.append(user_name)
                        tags = list(instance_tags.get(full_name))
            logger.info(f'UserName :: {usernames} {tags}')
            user_ids.extend(usernames)
        return user_ids

    def get_bucket_tags_to_add(self, instance_tags: list, bucket_tags: list):
        """
        This method retuns the tags to add buckets
        @param instance_tags:
        @param bucket_tags:
        @return:
        """
        add_tags = []
        for bucket_tag in bucket_tags:
            found = False
            for instance_tag in instance_tags:
                if instance_tag.get('Key') == bucket_tag.get('Key'):
                    found = True
            if not found:
                add_tags.append(bucket_tag)
        return add_tags

    def cluster_s3_bucket(self, instance_tags: dict):
        """
        This method removes the tags of buckets and add the buckets
        @param instance_tags:
        @return:
        """
        cluster_names = [name.split('/')[-1] for name in instance_tags.keys()]
        bucket_ids = []
        response = self.s3_client.list_buckets()
        for cluster_name in cluster_names:
            for bucket in response['Buckets']:
                if bucket['Name'].startswith(cluster_name):
                    bucket_tags = self.s3_client.get_bucket_tagging(Bucket=bucket.get('Name'))
                    if bucket_tags:
                        bucket_tags = bucket_tags['TagSet']
                        full_name = f'{self.cluster_prefix}{cluster_name}'
                        added_tags = instance_tags.get(full_name)
                        added_tags.append({'Key': 'CreationDate', 'Value': str(bucket.get('CreationDate'))})
                        add_tags = self.get_bucket_tags_to_add(added_tags, bucket_tags)
                        if self.cluster_name:
                            if self.cluster_name in bucket.get('Name'):
                                self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                                logger.info(f'BucketName :: {bucket.get("Name")} {added_tags}')
                                bucket_ids.append(bucket.get("Name"))
                        else:
                            self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                            logger.info(f'BucketName :: {bucket.get("Name")} {added_tags}')
                            bucket_ids.append(bucket.get("Name"))
                        break
        return bucket_ids
