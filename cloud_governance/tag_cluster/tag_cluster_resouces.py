from datetime import datetime

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger

from cloud_governance.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources


class TagClusterResources:
    """
    This class filter cluster resources by cluster name, and update tags when passing input_tags
    """
    
    SHORT_ID = 5
    
    def __init__(self, cluster_name: str = None, cluster_prefix: str = None, input_tags: dict = None,
                 region: str = 'us-east-2', dry_run: str = 'yes', cluster_only: bool = False):
        self.ec2_operations = EC2Operations(region=region)
        self.iam_operations = IAMOperations()
        self.utils = Utils(region=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.cluster_only = cluster_only
        self.s3_client = boto3.client('s3')
        self.cluster_prefix = cluster_prefix
        self.cluster_name = cluster_name
        self.cluster_key = self.__init_cluster_name()
        self.input_tags = input_tags
        self.cloudtrail = CloudTrailOperations(region_name='us-east-1')
        self.__get_username_from_instance_id_and_time = CloudTrailOperations(region_name=region).get_username_by_instance_id_and_time
        self.dry_run = dry_run
        self.non_cluster_update = TagNonClusterResources(region=region, dry_run=dry_run, input_tags=input_tags)

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
            value = f'{cluster_name.split("/")[-1]}-{resource_id.split("-")[0]}-{resource_id[-self.SHORT_ID:]}'
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

    def get_date_from_date(self, date_time: datetime):
        return date_time.strftime('%Y/%m/%d')

    def get_date_from_date_time(self, date_time: datetime):
        return date_time.strftime('%Y/%m/%d %H:%M:%S')

    def __remove_tags_start_with_aws(self, tags: list):
        """
        This method removes tags starting with aws
        @param tags:
        @return:
        """
        filter_tags = []
        for tag in tags:
            if not tag.get('Key').startswith('aws'):
                filter_tags.append(tag)
        return filter_tags

    def __generate_cluster_resources_list_by_tag(self, resources_list: list, input_resource_id: str, tags: str = 'Tags'):
        """
        This method return resource list that related to input resource id according to cluster's tag name and update the tags
        @param resources_list:
        @param input_resource_id:
        @param ids:
        @param tags:
        @return:
        """
        cluster_ids = {}
        cluster_tags = {}
        for resource in resources_list:
            resource_id = resource[input_resource_id]
            if resource.get(tags):
                # search that not exist permanent tags in the resource
                if not self.__validate_existing_tag(resource.get(tags)):
                    for tag in resource[tags]:
                        if self.cluster_prefix in tag.get('Key'):
                            if tag.get('Key') not in cluster_tags:
                                cluster_tags[tag.get('Key')] = []
                                cluster_ids[tag.get('Key')] = []
                                add_tags = self.__append_input_tags(resource.get(tags))
                                instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                                add_tags.extend(instance_tags)
                                add_tags = self.__check_name_in_tags(tags=add_tags, resource_id=resource_id)
                                add_tags = self.__remove_tags_start_with_aws(add_tags)
                                add_tags = self.__filter_resource_tags_by_add_tags(resource.get(tags), add_tags)
                                if add_tags:
                                    cluster_tags[tag.get('Key')].extend(add_tags)
                                    cluster_ids[tag.get('Key')].append(resource_id)
                            else:
                                cluster_ids[tag.get('Key')].append(resource_id)
        result_resources_list = []
        for cluster_name, cluster_id in cluster_ids.items():
            if self.cluster_name in cluster_name:
                if self.dry_run == "no":
                    self.ec2_client.create_tags(Resources=cluster_id, Tags=cluster_tags.get(cluster_name))
                    logger.info(f'{input_resource_id} :: {cluster_id} :: {cluster_name} :: {len(cluster_id)} :: {cluster_tags.get(cluster_name)}')
                result_resources_list.extend(cluster_id)
            else:
                if self.dry_run == "no":
                    self.ec2_client.create_tags(Resources=cluster_id, Tags=cluster_tags.get(cluster_name))
                    logger.info(f'{input_resource_id} :: {cluster_id} :: {len(cluster_id)} :: {cluster_tags.get(cluster_name)}')
                result_resources_list.extend(cluster_id)
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
        ec2s_data = self.ec2_operations.get_instances()
        for items in ec2s_data:
            if items.get('Instances'):
                instances_list.append(items['Instances'])
        return instances_list

    def remove_creation_date(self, tags: list):
        return [tag for tag in tags if tag.get('Key') != 'CreationDate']

    def __check_user_in_username_tags(self, tags: list):
        """
        This method check User tag in username tags
        @param tags:
        @return:
        """
        for tag in tags:
            if tag.get('Key') == 'User':
                return True
        return False

    def __validate_existing_tag(self, tags: list):
        """
        This method validates that permanent tag exists in tags list
        @param tags:
        @return:
        """
        for tag in tags:
            for key, value in self.input_tags.items():
                if tag.get('Key') == key:
                    return True
        return False

    def update_cluster_tags(self, resources: list):
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
                    # search that not exist permanent tags in the resource
                    if not self.__validate_existing_tag(item.get('Tags')):
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
                                        if username == 'AutoScaling':
                                            add_tags.append({'Key': 'User', 'Value': username})
                                            add_tags.append(({'Key': 'Manager', 'Value': 'NA'}))
                                            add_tags.append(({'Key': 'Email', 'Value': 'NA'}))
                                            add_tags.append(({'Key': 'Project', 'Value': 'NA'}))
                                            add_tags.append(({'Key': 'Environment', 'Value': 'NA'}))
                                            add_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
                                            logger.info(f'Autoscaling instance :: {instance_id}')
                                        else:
                                            user_tags = self.iam_operations.get_user_tags(username=username)
                                            if not self.__check_user_in_username_tags(user_tags):
                                                try:
                                                    user = self.iam_client.get_user(UserName=username)['User']
                                                    username = self.cloudtrail.get_username_by_instance_id_and_time(
                                                        start_time=user.get('CreateDate'), resource_id=username,
                                                        resource_type='AWS::IAM::User')
                                                    user_tags = self.iam_operations.get_user_tags(username=username)
                                                except:
                                                    add_tags.append({'Key': 'User', 'Value': username})
                                            if user_tags:
                                                add_tags.extend(user_tags)
                                                add_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
                                            else:
                                                add_tags.append({'Key': 'User', 'Value': username})
                                                add_tags.append(({'Key': 'Manager', 'Value': 'NA'}))
                                                add_tags.append(({'Key': 'Email', 'Value': 'NA'}))
                                                add_tags.append(({'Key': 'Project', 'Value': 'NA'}))
                                                add_tags.append(({'Key': 'Environment', 'Value': 'NA'}))
                                                add_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
                                    else:
                                        username = 'NA'
                                        add_tags.append({'Key': 'User', 'Value': username})
                                        add_tags.append(({'Key': 'Manager', 'Value': username}))
                                        add_tags.append(({'Key': 'Email', 'Value': username}))
                                        add_tags.append(({'Key': 'Project', 'Value': username}))
                                        add_tags.append(({'Key': 'Environment', 'Value': username}))
                                        add_tags.append(({'Key': 'Owner', 'Value': username}))
                                    add_tags.append({'Key': 'LaunchTime', 'Value': self.get_date_from_date_time(item.get('LaunchTime'))})
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
                        try:
                            self.ec2_client.create_tags(Resources=instance_ids, Tags=cluster_tags.get(cluster_instance_name))
                            logger.info(f'Cluster :: {cluster_instance_name} :: InstanceId :: {instance_ids} :: {cluster_tags.get(cluster_instance_name)}')
                        except Exception as err:
                            logger.info(err)
                    result_instance_list.extend(instance_ids)
            else:
                if self.dry_run == 'no':
                    try:
                        self.ec2_client.create_tags(Resources=instance_ids, Tags=cluster_tags.get(cluster_instance_name))
                        logger.info(f'Cluster :: {cluster_instance_name} :: InstanceId :: {instance_ids} :: {cluster_tags.get(cluster_instance_name)}')
                    except Exception as err:
                        logger.info(err)
                result_instance_list.extend(instance_ids)
        logger.info(f'cluster_instance :: {len(result_instance_list)} :: {result_instance_list}')
        if not self.cluster_key:
            self.cluster_role(list(cluster_instances.keys()))
            self.cluster_user(list(cluster_instances.keys()))
            self.cluster_s3_bucket(list(cluster_instances.keys()))
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
            if not self.cluster_only:
                ids = self.update_cluster_tags(cluster)
                self.non_cluster_update.non_cluster_update_ec2(non_cluster)
                return ids
            else:
                ids = self.update_cluster_tags(cluster)
                return ids
        else:
            return []

    def cluster_volume(self):
        """
        This method return list of cluster's volume according to cluster tag name
        @return:
        """
        volumes_data = self.ec2_operations.get_volumes()
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(volumes_data)
        if not self.cluster_only:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'VolumeId')
            self.non_cluster_update.update_volumes(non_cluster)
        else:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'VolumeId')
        return ids

    def cluster_ami(self):
        """
        This method return list of cluster's ami according to cluster tag name
        @return:
        """
        images_data = self.ec2_operations.get_images()
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(images_data)
        if not self.cluster_only:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'ImageId')
            self.non_cluster_update.update_ami(non_cluster)
        else:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'ImageId')
        return ids

    def cluster_snapshot(self):
        """
        This method return list of cluster's snapshot according to cluster tag name
        @return:
        """
        snapshots_data = self.ec2_operations.get_snapshots()
        cluster, non_cluster = self.ec2_operations.scan_cluster_non_cluster_resources(snapshots_data)
        if not self.cluster_only:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'SnapshotId')
            self.non_cluster_update.update_snapshots(non_cluster)
        else:
            ids = self.__generate_cluster_resources_list_by_tag(cluster, 'SnapshotId')
        return ids

    def __get_security_group_data(self):
        """
        This method return security group data
        @return:
        """
        return self.ec2_operations.get_security_groups()

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
        elastic_ips_data = self.ec2_operations.get_elastic_ips()
        elastic_ips = self.__generate_cluster_resources_list_by_tag(resources_list=elastic_ips_data,
                                                                    input_resource_id='AllocationId')
        logger.info(f'cluster_elastic_ip count: {len(sorted(elastic_ips))} {sorted(elastic_ips)}')
        return sorted(elastic_ips)

    def cluster_network_interface(self):
        """
        This method return list of cluster's network interface according to cluster tag name
        @return:
        """
        network_interfaces_data = self.ec2_operations.get_network_interface()
        network_interface_ids = self.__generate_cluster_resources_list_by_tag(resources_list=network_interfaces_data,
                                                                              input_resource_id='NetworkInterfaceId',
                                                                              tags='TagSet')
        logger.info(f'cluster_network_interface count: {len(sorted(network_interface_ids))} {sorted(network_interface_ids)}')
        return sorted(network_interface_ids)

    def cluster_load_balancer(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        @return:
        """
        result_resources_list = []
        load_balancers_data = self.ec2_operations.get_load_balancers()
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerName']
            tags = self.elb_client.describe_tags(LoadBalancerNames=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    if not self.__validate_existing_tag(item.get('Tags')):
                        for tag in item['Tags']:
                            if self.cluster_prefix in tag.get('Key'):
                                all_tags = []
                                instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                                if not instance_tags:
                                    all_tags = self.__append_input_tags(item.get('Tags'))
                                all_tags.extend(instance_tags)
                                all_tags = self.__remove_tags_start_with_aws(all_tags)
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
        logger.info(f'cluster_load_balancer count: {len(sorted(result_resources_list))} {sorted(result_resources_list)}')
        return sorted(result_resources_list)

    def cluster_load_balancer_v2(self):
        """
        This method return list of cluster's load balancer according to cluster vpc
        @return:
        """
        result_resources_list = []
        load_balancers_data = self.ec2_operations.get_load_balancers_v2()
        for resource in load_balancers_data:
            resource_id = resource['LoadBalancerArn']
            tags = self.elbv2_client.describe_tags(ResourceArns=[resource_id])
            for item in tags['TagDescriptions']:
                if item.get('Tags'):
                    if not self.__validate_existing_tag(item.get('Tags')):
                        for tag in item['Tags']:
                            if self.cluster_prefix in tag.get('Key'):
                                all_tags = []
                                instance_tags = self.__get_cluster_tags_by_instance_cluster(cluster_name=tag.get('Key'))
                                if not instance_tags:
                                    all_tags = self.__append_input_tags(item.get('Tags'))
                                all_tags.extend(instance_tags)
                                all_tags = self.__remove_tags_start_with_aws(all_tags)
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
        logger.info(f'cluster_load_balancer_v2 count: {len(sorted(result_resources_list))} {sorted(result_resources_list)}')
        return sorted(result_resources_list)

    def cluster_vpc(self):
        """
        This method return list of cluster's vpc according to cluster tag name
        @return:
        """
        vpcs_data = self.ec2_operations.get_vpcs()
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
        vpcs_data = self.ec2_operations.get_vpcs()
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
        subnets_data = self.ec2_operations.get_subnets()
        subnet_ids = self.__generate_cluster_resources_list_by_tag(resources_list=subnets_data,
                                                                   input_resource_id='SubnetId')
        logger.info(f'cluster_subnet count: {len(sorted(subnet_ids))} {sorted(subnet_ids)}')
        return sorted(subnet_ids)

    def cluster_route_table(self):
        """
        This method return list of cluster's route table according to cluster tag name
        @return:
        """
        route_tables_data = self.ec2_operations.get_route_tables()
        route_table_ids = self.__generate_cluster_resources_list_by_tag(resources_list=route_tables_data,
                                                                        input_resource_id='RouteTableId')
        logger.info(f'cluster_route_table count: {len(sorted(route_table_ids))} {sorted(route_table_ids)}')
        return sorted(route_table_ids)

    def cluster_internet_gateway(self):
        """
        This method return list of cluster's route table internet gateway according to cluster tag name
        @return:
        """
        internet_gateways_data = self.ec2_operations.get_internet_gateways()
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
        dhcp_options_data = self.ec2_operations.get_dhcp_options()
        dhcp_ids = self.__generate_cluster_resources_list_by_tag(resources_list=dhcp_options_data,
                                                                 input_resource_id='DhcpOptionsId')
        logger.info(f'cluster_dhcp_option count: {len(sorted(dhcp_ids))} {sorted(dhcp_ids)}')
        return sorted(dhcp_ids)

    def cluster_vpc_endpoint(self):
        """
        This method return list of cluster's vpc endpoint according to cluster tag name
        @return:
        """
        vpc_endpoints_data = self.ec2_operations.get_vpce()
        vpc_endpoint_ids = self.__generate_cluster_resources_list_by_tag(resources_list=vpc_endpoints_data,
                                                                         input_resource_id='VpcEndpointId')
        logger.info(f'cluster_vpc_endpoint count: {len(sorted(vpc_endpoint_ids))} {sorted(vpc_endpoint_ids)}')
        return sorted(vpc_endpoint_ids)

    def cluster_nat_gateway(self):
        """
        This method return list of cluster's nat gateway according to cluster tag name
        @return:
        """
        nat_gateways_data = self.ec2_operations.get_nat_gateways()
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
        network_acls_data = self.ec2_operations.get_nacls()
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
                    role_name_list = []
                    roles = self.iam_operations.get_roles()
                    for role in roles:
                        if cluster_key in role.get('RoleName'):
                            role_name_list.append(role.get('RoleName'))
                    if role_name_list:
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
                                all_tags = self.__remove_tags_start_with_aws(all_tags)
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
                    else:
                        logger.info(f'Missing role for cluster {cluster_name}')
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
                users = self.iam_operations.get_users()
                # return self.__generate_cluster_resources_list_by_tag(resources_list=users_data,
                #                                                      input_resource_id='UserId')
                cluster_name = self.cluster_name if self.cluster_key else cluster_name
                for user in users:
                    user_name = user['UserName']
                    if cluster_name in user_name:
                        user_data = self.iam_client.get_user(UserName=user_name)
                        data = user_data['User']
                        if data.get('Tags'):
                            # search that not exist permanent tags in the resource
                            if not self.__validate_existing_tag(data.get('Tags')):
                                for tag in data['Tags']:
                                    if cluster_name in tag['Key']:
                                        all_tags = []
                                        instance_tags = self.__get_cluster_tags_by_instance_cluster(
                                            cluster_name=f'{self.cluster_prefix}{cluster_name}')
                                        if not instance_tags:
                                            all_tags = self.__append_input_tags(data.get('Tags'))
                                        all_tags.extend(instance_tags)
                                        all_tags = self.__remove_tags_start_with_aws(all_tags)
                                        all_tags = self.__filter_resource_tags_by_add_tags(data.get('Tags'), all_tags)
                                        if all_tags:
                                            if self.dry_run == 'no':
                                                try:
                                                    self.iam_client.tag_user(UserName=user_name, Tags=all_tags)
                                                    logger.info(all_tags)
                                                except Exception as err:
                                                    logger.info(err)
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
                                # search that not exist permanent tags in the resource
                                if not self.__validate_existing_tag(bucket_tags):
                                    add_tags = []
                                    instance_tags = self.__get_cluster_tags_by_instance_cluster(
                                        cluster_name=f'{self.cluster_prefix}{cluster_name}')
                                    if not instance_tags:
                                        add_tags = self.__append_input_tags(bucket_tags)
                                    add_tags.extend(instance_tags)
                                    add_tags = self.__remove_tags_start_with_aws(add_tags)
                                    add_tags = self.__filter_resource_tags_by_add_tags(bucket_tags, add_tags)
                                    if add_tags:
                                        if self.dry_run == 'no':
                                            try:
                                                add_tags.extend(bucket_tags)
                                                self.s3_client.put_bucket_tagging(Bucket=bucket.get('Name'), Tagging={'TagSet': add_tags})
                                                logger.info(add_tags)
                                            except Exception as err:
                                                logger.info(err)
                                        bucket_result_list.append(bucket['Name'])
        logger.info(f'cluster_s3_bucket count: {len(sorted(bucket_result_list))} {sorted(bucket_result_list)}')
        return sorted(bucket_result_list)
