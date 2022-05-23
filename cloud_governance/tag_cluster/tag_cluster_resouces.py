from multiprocessing import Process, Queue

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger

# @todo add next token
# response = client.get_servers()
# results = response["serverList"]
# while "NextToken" in response:
#     response = client.get_servers(NextToken=response["NextToken"])
#     results.extend(response["serverList"])
from cloud_governance.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources


class TagClusterResources:
    """
    This class filter cluster resources by cluster name, and update tags when passing input_tags
    """
    volume_ids = []

    def __init__(self, cluster_name: str = None, cluster_prefix: str = None, input_tags: dict = None,
                 region: str = 'us-east-2', dry_run: str = 'yes'):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.iam_operations = IAMOperations()
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.cluster_key = self.__init_cluster_name()
        self.input_tags = input_tags
        self.__get_details_resource_list = Utils().get_details_resource_list
        self.__get_username_from_instance_id_and_time = CloudTrailOperations(
            region_name=region).get_username_by_instance_id_and_time
        self.dry_run = dry_run
        self.non_cluster_update = TagNonClusterResources(region=region, dry_run=dry_run, input_tags=input_tags)
        self.ids = []
        self.ec2_operations = EC2Operations()

    def __init_cluster_name(self):
        """
        This method find the cluster full stamp key according to user cluster name, scan instance and if not found scan security group
        i.e.: user cluster name = test , cluster stamp key =  kubernetes.io/cluster/test-jlhpd
        @return:
        """
        return self.__scan_cluster_security_groups()

    def __input_tags_list_builder(self):
        """
        This method build tags list according to input tags dictionary
        @return:
        """
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def __append_input_tags(self, current_tags: list = None):
        """
        This method append the input tags to the current tags, and return the input tags
        @param current_tags:
        @return:
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
        """
        This method checks Name is present in the Tags or not, if not ot add Name tag
        @param tags:
        @param resource_id:
        @return:
        """
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
            value = f'{cluster_name.split("/")[-1]}-{resource_id.split("-")[0]}-{resource_id[-4:]}'
            tags.append({'Key': 'Name', 'Value': value})
        return tags

    def __get_cluster_tags_by_instance_cluster(self, cluster_name: str):
        """
        This method get the cluster instance tags by cluster name
        @param cluster_name:
        @return:
        """
        instances_list = self.__get_instances_data()
        if instances_list:
            for instance in instances_list:
                for item in instance:
                    if item.get('Tags'):
                        for tag in item.get('Tags'):
                            if self.cluster_prefix in tag.get('Key'):
                                if tag.get('Key') == cluster_name:
                                    i_tags = [instance_tag for instance_tag in item.get('Tags') if
                                              instance_tag.get('Key') != 'Name']
                                    return [i_tag for i_tag in i_tags if i_tag.get('Key') != cluster_name]
        return []

    def __generate_cluster_resources_list_by_tag(self, resources_list: list, input_resource_id: str, ids=None,
                                                 tags: str = 'Tags'):
        """
        This method return resource list that related to input resource id according to cluster's tag name and update the tags
        @param resources_list:
        @param input_resource_id:
        @param ids:
        @param tags:
        @return:
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
                        if resource.get('CreateTime'):
                            add_tags = self.__remove_launchTime(add_tags)
                            add_tags.append({'Key': 'CreateTime', 'Value': str(resource.get('CreateTime'))})
                        elif resource.get('StartTime'):
                            add_tags = self.__remove_launchTime(add_tags)
                            add_tags.append({'Key': 'StartTime', 'Value': str(resource.get('StartTime'))})
                        add_tags = self.__filter_resource_tags_by_add_tags(resource.get(tags), add_tags)
                        if add_tags:
                            if self.cluster_name:
                                cluster_resource_name = tag.get('Key').split('/')[-1]
                                if cluster_resource_name == self.cluster_name:
                                    if self.dry_run == "no":
                                        self.ec2_client.create_tags(Resources=[resource_id], Tags=add_tags)
                                        logger.info(add_tags)
                                    result_resources_list.append(resource_id)
                            else:
                                if self.dry_run == "no":
                                    self.ec2_client.create_tags(Resources=[resource_id], Tags=add_tags)
                                    logger.info(add_tags)
                                result_resources_list.append(resource_id)
        if ids is not None:
            ids.put(sorted(result_resources_list))
        else:
            ids = sorted(result_resources_list)
        if input_resource_id == 'ImageId':
            logger.info(f'cluster_ami count: {len(result_resources_list)} {sorted(result_resources_list)}')
        elif input_resource_id == 'VolumeId':
            logger.info(f'cluster_volume count: {len(result_resources_list)} {sorted(result_resources_list)}')
        elif input_resource_id == 'SnapshotId':
            logger.info(f'cluster_snapshot count: {len(result_resources_list)} {result_resources_list}')
        return ids

    def __generate_cluster_resources_list_by_vpc(self, resources_list: list, input_resource_id: str):
        """
        This method return resource list that related to input resource id according to cluster's vpc id
        @param resources_list:
        @param input_resource_id:
        @return:
        """
        result_resources_list = []
        vpc_data = self.get_cluster_vpc()
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get('VpcId'):
                for vpc_id in vpc_data.keys():
                    if resource.get('VpcId') == vpc_id:
                        all_tags = []
                        all_tags.extend(vpc_data.get(vpc_id))
                        all_tags = self.__check_name_in_tags(tags=all_tags, resource_id=resource_id)
                        all_tags = self.__filter_resource_tags_by_add_tags(resource.get('Tags'), all_tags)
                        cluster_tag = [tag for tag in vpc_data.get(vpc_id) if self.cluster_prefix in tag.get('Key')]
                        if all_tags:
                            if self.cluster_name:
                                if self.cluster_name in cluster_tag[0].get('Key'):
                                    if self.dry_run == 'no':
                                        self.ec2_client.create_tags(Resources=[resource_id], Tags=all_tags)
                                        logger.info(all_tags)
                                    result_resources_list.append(resource_id)
                            else:
                                if self.dry_run == 'no':
                                    self.ec2_client.create_tags(Resources=[resource_id], Tags=all_tags)
                                    logger.info(all_tags)
                                result_resources_list.append(resource_id)
                        break
        return sorted(result_resources_list)

    def __scan_resource_for_cluster_fullname(self, resources_list: list, tags: str = 'Tags'):
        """
        This method scan for full cluster name according in input resource by input cluster name.
        @param resources_list:
        @param tags:
        @return:
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
        @return:
        """
        security_groups = self.__get_security_group_data()
        # scan security group for cluster stamp key
        return self.__scan_resource_for_cluster_fullname(resources_list=security_groups)

    def __get_instances_data(self):
        """
        This method go over all instances
        @return:
        """
        instances_list = []
        ec2s = self.ec2_client.describe_instances()
        ec2s_data = ec2s['Reservations']
        for items in ec2s_data:
            if items.get('Instances'):
                instances_list.append(items['Instances'])
        return instances_list

    def remove_creation_date(self, tags: list):
        return [tag for tag in tags if tag.get('Key') != 'CreationDate']

    def update_cluster_tags(self, resources: list, queue):
        """
        This method update the Cluster instance tags and returns the updated tags list ids.
        @param resources:
        @param queue:
        @return:
        """
        cluster_instances = {}
        result_instance_list = []
        cluster_tags = {}
        for instance in resources:
            for item in instance:
                instance_id = item['InstanceId']
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_prefix in tag.get('Key'):
                            add_tags = self.__append_input_tags()
                            cluster_name = tag.get('Key').split('/')[-1]
                            if cluster_name in cluster_instances:
                                add_tags = self.__filter_resource_tags_by_add_tags(tags=item.get('Tags'),
                                                                                   search_tags=cluster_tags[
                                                                                       cluster_name])
                                if add_tags:
                                    cluster_instances[cluster_name].append(instance_id)
                                break
                            else:
                                username = self.__get_username_from_instance_id_and_time(
                                    start_time=item.get('LaunchTime'), resource_id=instance_id,
                                    resource_type='AWS::EC2::Instance')
                                if username:
                                    user_tags = self.iam_operations.get_user_tags(username=username)
                                    add_tags.extend(user_tags)
                                    add_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
                                add_tags.append({'Key': 'LaunchTime', 'Value': str(item.get('LaunchTime'))})
                                add_tags = self.remove_creation_date(add_tags)
                                add_tags = self.__filter_resource_tags_by_add_tags(tags=item.get('Tags'),
                                                                                   search_tags=add_tags)
                                if add_tags:
                                    cluster_instances[cluster_name] = [instance_id]
                                    cluster_tags[cluster_name] = add_tags
                                break
        for cluster_instance_name, instance_ids in cluster_instances.items():
            if self.cluster_name:
                if cluster_instance_name == self.cluster_name:
                    if self.dry_run == 'no':
                        self.ec2_client.create_tags(Resources=instance_ids,
                                                    Tags=cluster_tags.get(cluster_instance_name))
                        logger.info(cluster_tags.get(cluster_instance_name))
                    result_instance_list.extend(instance_ids)
            else:
                if self.dry_run == 'no':
                    self.ec2_client.create_tags(Resources=instance_ids,
                                                Tags=cluster_tags.get(cluster_instance_name))
                    logger.info(cluster_tags.get(cluster_instance_name))
                result_instance_list.extend(instance_ids)

        logger.info(f'cluster_instance count: {len(sorted(result_instance_list))} {sorted(result_instance_list)}')
        if not self.cluster_key:
            jobs = []
            iam_list = [self.cluster_role, self.cluster_s3_bucket, self.cluster_user]
            for iam in iam_list:
                p = Process(target=iam, args=(list(cluster_instances.keys()),))
                jobs.append(p)
                p.start()
            for job in jobs:
                job.join()
        queue.put(sorted(result_instance_list))
        return sorted(result_instance_list)

    def cluster_instance(self):
        """
        This method return list of cluster's instance according to cluster tag name,
        The instances list is different from other resources
        it will search for full cluster name (including random suffix string) in case of user input cluster name was given
        @return:
        """
        self.cluster_key = self.__init_cluster_name()
        instances_list = self.__get_instances_data()
        if instances_list:
            cluster, non_cluster = self.ec2_operations.scan_cluster_or_non_cluster_instance(instances_list)
            ids = Queue()
            cluster_process = Process(target=self.update_cluster_tags, args=(cluster, ids,))
            non_cluster_process = Process(target=self.non_cluster_update.non_cluster_update_ec2, args=(non_cluster,))
            cluster_process.start()
            non_cluster_process.start()
            cluster_process.join()
            non_cluster_process.join()
            return ids.get()

    def cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        @return:
        """
        volumes = self.ec2_client.describe_volumes()
        volumes_data = volumes['Volumes']
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(volumes_data)
        ids = Queue()
        cluster_process = Process(target=self.__generate_cluster_resources_list_by_tag,
                                  args=(cluster, 'VolumeId', ids,))
        non_cluster_process = Process(target=self.non_cluster_update.update_volumes, args=(non_cluster,))
        cluster_process.start()
        non_cluster_process.start()
        cluster_process.join()
        non_cluster_process.join()
        return ids.get()

    def cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        @return:
        """
        images = self.ec2_client.describe_images(Owners=['self'])
        images_data = images['Images']
        ids = Queue()
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(images_data)
        cluster_process = Process(target=self.__generate_cluster_resources_list_by_tag, args=(cluster, 'ImageId',ids, ))
        non_cluster_process = Process(target=self.non_cluster_update.update_ami, args=(non_cluster,))
        cluster_process.start()
        non_cluster_process.start()
        cluster_process.join()
        non_cluster_process.join()
        return ids.get()

    def cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        @return:
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots_data = snapshots['Snapshots']
        ids = Queue()
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(snapshots_data)
        cluster_process = Process(target=self.__generate_cluster_resources_list_by_tag, args=(cluster, 'SnapshotId',ids, ))
        non_cluster_process = Process(target=self.non_cluster_update.update_snapshots, args=(non_cluster,))
        cluster_process.start()
        non_cluster_process.start()
        cluster_process.join()
        non_cluster_process.join()
        return ids.get()

    def __get_security_group_data(self):
        """
        This method return security group data
        @return:
        """
        security_groups = self.ec2_client.describe_security_groups()
        return security_groups['SecurityGroups']

    def cluster_security_group(self):
        """
        This method return list of cluster's security group according to cluster tag name
        @return:
        """
        security_group_ids = self.__generate_cluster_resources_list_by_tag(
            resources_list=self.__get_security_group_data(),
            input_resource_id='GroupId')
        logger.info(f'cluster_security_group count: {len(sorted(security_group_ids))} {sorted(security_group_ids)}')

    def cluster_elastic_ip(self):
        """
        This method return list of cluster's elastic ip according to cluster tag name
        @return:
        """
        elastic_ips = self.ec2_client.describe_addresses()
        elastic_ips_data = elastic_ips['Addresses']
        elastic_ips = self.__generate_cluster_resources_list_by_tag(resources_list=elastic_ips_data,
                                                                    input_resource_id='AllocationId')
        logger.info(f'cluster_elastic_ip count: {len(sorted(elastic_ips))} {sorted(elastic_ips)}')
        return sorted(elastic_ips)

    def cluster_network_interface(self):
        """
        This method return list of cluster's network interface according to cluster tag name
        @return:
        """
        network_interfaces = self.ec2_client.describe_network_interfaces()
        network_interfaces_data = network_interfaces['NetworkInterfaces']
        network_interface_ids = self.__generate_cluster_resources_list_by_tag(resources_list=network_interfaces_data,
                                                                              input_resource_id='NetworkInterfaceId',
                                                                              tags='TagSet')
        logger.info(
            f'cluster_network_interface count: {len(sorted(network_interface_ids))} {sorted(network_interface_ids)}')
        return sorted(network_interface_ids)

    def cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        @return:
        """
        result_resources_list = []
        load_balancers = self.elb_client.describe_load_balancers()
        load_balancers_data = load_balancers['LoadBalancerDescriptions']
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerName']
            tags = self.elb_client.describe_tags(LoadBalancerNames=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    for tag in item['Tags']:
                        if self.cluster_prefix in tag.get('Key'):
                            all_tags = []
                            instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                            if not instance_tags:
                                all_tags = self.__append_input_tags(item.get('Tags'))
                            all_tags.extend(instance_tags)
                            all_tags = self.__remove_launchTime(all_tags)
                            all_tags.append({'Key': 'CreatedTime', 'Value': str(resource.get('CreatedTime'))})
                            all_tags = self.__filter_resource_tags_by_add_tags(item.get('Tags'), all_tags)
                            if all_tags:
                                if self.cluster_name:
                                    if tag['Key'] == self.cluster_key:
                                        try:
                                            if self.dry_run == 'no':
                                                self.elb_client.add_tags(LoadBalancerNames=[resource_id], Tags=all_tags)
                                                logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                        result_resources_list.append(resource_id)
                                    break
                                else:
                                    if self.dry_run == 'no':
                                        try:
                                            self.elb_client.add_tags(LoadBalancerNames=[resource_id], Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
                            break
        logger.info(
            f'cluster_load_balancer count: {len(sorted(result_resources_list))} {sorted(result_resources_list)}')
        return sorted(result_resources_list)

    def cluster_load_balancer_v2(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        @return:
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
                        if self.cluster_prefix in tag.get('Key'):
                            all_tags = []
                            instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                            if not instance_tags:
                                all_tags = self.__append_input_tags(item.get('Tags'))
                            all_tags.extend(instance_tags)
                            all_tags = self.__remove_launchTime(all_tags)
                            all_tags.append({'Key': 'CreatedTime', 'Value': str(resource.get('CreatedTime'))})
                            all_tags = self.__filter_resource_tags_by_add_tags(item.get('Tags'), all_tags)
                            if all_tags:
                                if self.cluster_name:
                                    if tag['Key'] == self.cluster_key:
                                        try:
                                            if self.dry_run == 'no':
                                                self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                                logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                        result_resources_list.append(resource_id)
                                    break
                                else:
                                    if self.dry_run == 'no':
                                        try:
                                            self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=all_tags)
                                            logger.info(all_tags)
                                        except Exception as err:
                                            logger.exception(f'Tags are already updated, {err}')
                                    result_resources_list.append(resource_id)
                                    break
                            break
        logger.info(
            f'cluster_load_balancer_v2 count: {len(sorted(result_resources_list))} {sorted(result_resources_list)}')
        return sorted(result_resources_list)

    def cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        @return:
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        vpc_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpcs_data, input_resource_id='VpcId')
        logger.info(f'cluster_vpc count: {len(sorted(vpc_ids))} {sorted(vpc_ids)}')
        self.cluster_network_acl()
        return sorted(vpc_ids)

    def get_cluster_vpc(self):
        """
        This method get cluster vpc ids and it's tags.
        Missing OpenShift Tags for it based on VPCs
        @return:
        """
        vpcs = self.ec2_client.describe_vpcs()
        vpcs_data = vpcs['Vpcs']
        vpc_ids = {}
        for vpc in vpcs_data:
            if vpc.get('Tags'):
                for tag in vpc.get('Tags'):
                    if self.cluster_prefix in tag.get('Key'):
                        vpc_ids[vpc.get('VpcId')] = [tag for tag in vpc.get('Tags') if tag.get('Key') != 'Name']
                        break
        return vpc_ids

    def cluster_subnet(self):
        """
        This method return list of cluster's subnet according to cluster tag name
        @return:
        """
        subnets = self.ec2_client.describe_subnets()
        subnets_data = subnets['Subnets']
        subnet_ids = self.__generate_cluster_resources_list_by_tag(resources_list=subnets_data,
                                                                   input_resource_id='SubnetId')
        logger.info(f'cluster_subnet count: {len(sorted(subnet_ids))} {sorted(subnet_ids)}')
        return sorted(subnet_ids)

    def cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        @return:
        """
        route_tables = self.ec2_client.describe_route_tables()
        route_tables_data = route_tables['RouteTables']
        route_table_ids = self.__generate_cluster_resources_list_by_tag(resources_list=route_tables_data,
                                                                        input_resource_id='RouteTableId')
        logger.info(f'cluster_route_table count: {len(sorted(route_table_ids))} {sorted(route_table_ids)}')
        return sorted(route_table_ids)

    def cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        @return:
        """
        internet_gateways = self.ec2_client.describe_internet_gateways()
        internet_gateways_data = internet_gateways['InternetGateways']
        internet_gateway_ids = self.__generate_cluster_resources_list_by_tag(resources_list=internet_gateways_data,
                                                                             input_resource_id='InternetGatewayId')
        logger.info(
            f'cluster_internet_gateway count: {len(sorted(internet_gateway_ids))} {sorted(internet_gateway_ids)}')
        return sorted(internet_gateway_ids)

    def cluster_dhcp_option(self):
        """
        This method return list of cluster's dhcp option according to cluster tag name
        @return:
        """
        dhcp_options = self.ec2_client.describe_dhcp_options()
        dhcp_options_data = dhcp_options['DhcpOptions']
        dhcp_ids = self.__generate_cluster_resources_list_by_tag(resources_list=dhcp_options_data,
                                                                 input_resource_id='DhcpOptionsId')
        logger.info(f'cluster_dhcp_option count: {len(sorted(dhcp_ids))} {sorted(dhcp_ids)}')
        return sorted(dhcp_ids)

    def cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        @return:
        """
        vpc_endpoints = self.ec2_client.describe_vpc_endpoints()
        vpc_endpoints_data = vpc_endpoints['VpcEndpoints']
        vpc_endpoint_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpc_endpoints_data,
                                                                         input_resource_id='VpcEndpointId')
        logger.info(f'cluster_vpc_endpoint count: {len(sorted(vpc_endpoint_ids))} {sorted(vpc_endpoint_ids)}')
        return sorted(vpc_endpoint_ids)

    def cluster_nat_gateway(self):
        """
        This method return list of cluster's nat gateway according to cluster tag name
        @return:
        """
        nat_gateways = self.ec2_client.describe_nat_gateways()
        nat_gateways_data = nat_gateways['NatGateways']
        nat_gateway_id = self.__generate_cluster_resources_list_by_tag(resources_list=nat_gateways_data,
                                                                       input_resource_id='NatGatewayId')
        logger.info(f'cluster_nat_gateway count: {len(sorted(nat_gateway_id))} {sorted(nat_gateway_id)}')
        return sorted(nat_gateway_id)

    def cluster_network_acl(self):
        """
        This method return list of cluster's network acl according to cluster vpc id
        Missing OpenShift Tags for it based on VPCs
        @return:
        """
        network_acls = self.ec2_client.describe_network_acls()
        network_acls_data = network_acls['NetworkAcls']
        network_acl_ids = self.__generate_cluster_resources_list_by_vpc(resources_list=network_acls_data,
                                                                        input_resource_id='NetworkAclId')
        logger.info(f'cluster_network_acl count: {len(network_acl_ids)}, {network_acl_ids}')
        return sorted(network_acl_ids)

    def cluster_role(self, cluster_names: list = []):
        """
        This method return list of cluster's role according to cluster name
        @param cluster_names:
        @return:
        """
        # tag_role
        result_role_list = []
        # if cluster_key exit
        if self.cluster_name:
            cluster_names.append(self.cluster_name)
        if cluster_names:
            for cluster_name in cluster_names:
                cluster_key = self.cluster_name if self.cluster_key else cluster_name
                if cluster_key:
                    # starts with cluster name, search for specific role name for fast scan (a lot of roles)
                    role_name_list = [f"{cluster_key}-master-role", f"{cluster_key}-worker-role"]

                    for role_name in role_name_list:
                        try:
                            role = self.iam_client.get_role(RoleName=role_name)
                            role_data = role['Role']
                            all_tags = []
                            instance_tags = self.__get_cluster_tags_by_instance_cluster(
                                cluster_name=f'{self.cluster_prefix}{cluster_key}')
                            if not instance_tags:
                                all_tags = self.__append_input_tags(role_data.get('Tags'))
                            else:
                                all_tags.extend(instance_tags)
                            all_tags = self.__remove_launchTime(all_tags)
                            all_tags.append({'Key': 'CreationDate', 'Value': str(role_data.get('CreateDate'))})
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
        logger.info(f'cluster_role count: {len(sorted(result_role_list))} {sorted(result_role_list)}')
        return sorted(result_role_list)

    def cluster_user(self, cluster_names: list = []):
        """
        This method return list of cluster's user according to cluster name
        @param cluster_names:
        @return:
        """
        # tag_user
        result_user_list = []
        if self.cluster_name:
            cluster_names.append(self.cluster_name)
        if cluster_names:
            for cluster_name in cluster_names:
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
                                    all_tags = []
                                    instance_tags = self.__get_cluster_tags_by_instance_cluster(
                                        cluster_name=f'{self.cluster_prefix}{cluster_name}')
                                    if not instance_tags:
                                        all_tags = self.__append_input_tags(data.get('Tags'))
                                    all_tags.extend(instance_tags)
                                    all_tags = self.__remove_launchTime(all_tags)
                                    all_tags.append({'Key': 'CreationDate', 'Value': str(data.get('CreateDate'))})
                                    all_tags = self.__filter_resource_tags_by_add_tags(data.get('Tags'), all_tags)
                                    if all_tags:
                                        if self.dry_run == 'no':
                                            self.iam_client.tag_user(UserName=user_name, Tags=all_tags)
                                            logger.info(all_tags)
                                        result_user_list.append(user_name)
                                    break
        logger.info(f'cluster_user count: {len(sorted(result_user_list))} {sorted(result_user_list)}')
        return sorted(result_user_list)

    def __filter_resource_tags_by_add_tags(self, tags: list, search_tags: list):
        """
        This method filters the tags by cluster and adding tags.
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

    def __remove_launchTime(self, tags: list):
        """
        This method removes the launch time form the instance tags
        @param tags:
        @return:
        """
        return [tag for tag in tags if tag.get('Key') != 'LaunchTime']

    def cluster_s3_bucket(self, cluster_names: list = []):
        """
        This method return list of cluster's s3 bucket according to cluster name
        @param cluster_names:
        @return:
        """
        bucket_result_list = []
        response = self.s3_client.list_buckets()
        # if cluster_key exit
        if self.cluster_name:
            cluster_names.append(self.cluster_name)
        if cluster_names:
            for cluster_name in cluster_names:
                cluster_key = self.cluster_name if self.cluster_key else cluster_name
                if cluster_key:
                    for bucket in response['Buckets']:
                        # starts with cluster name
                        if bucket['Name'].startswith(cluster_key):
                            bucket_tags = self.s3_client.get_bucket_tagging(Bucket=bucket.get('Name'))
                            if bucket_tags:
                                bucket_tags = bucket_tags['TagSet']
                                add_tags = []
                                instance_tags = self.__get_cluster_tags_by_instance_cluster(
                                    cluster_name=f'{self.cluster_prefix}{cluster_name}')
                                if not instance_tags:
                                    add_tags = self.__append_input_tags(bucket_tags)
                                add_tags.extend(instance_tags)
                                add_tags = self.__remove_launchTime(add_tags)
                                add_tags.append({'Key': 'CreationDate', 'Value': str(bucket.get('CreationDate'))})
                                add_tags = self.__filter_resource_tags_by_add_tags(bucket_tags, add_tags)
                                if add_tags:
                                    if self.dry_run == 'no':
                                        add_tags.extend(bucket_tags)
                                        self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'),
                                                                          Tagging={'TagSet': add_tags})
                                        logger.info(add_tags)
                                    bucket_result_list.append(bucket['Name'])
        logger.info(f'cluster_s3_bucket count: {len(sorted(bucket_result_list))} {sorted(bucket_result_list)}')
        return sorted(bucket_result_list)
