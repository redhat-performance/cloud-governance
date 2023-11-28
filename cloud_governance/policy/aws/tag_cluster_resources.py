from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.resource_tagging_api.resource_tag_api_operations import ResourceTagAPIOperations
from cloud_governance.common.clouds.aws.utils.common_operations import get_tag_name_and_value, \
    convert_key_values_to_dict
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.policy.policy_operations.aws.tagging.abstract_cluster_tagging_operations import \
    AbstractClusterTaggingOperations


class TagClusterResources(AbstractClusterTaggingOperations):
    """
    This class perform tagging on aws cluster resources that have an active EC2 instance
    """

    def __init__(self, region_name: str = '', cluster_name: str = ''):
        super().__init__(region_name=region_name, cluster_name=cluster_name)
        self.__ec2_resource_type = 'ec2:instance'
        self.__region_name = self._region_name

    def __get_ec2_instances_list(self):
        """
        This method returns the ec2 instances by region
        :return:
        :rtype:
        """
        ec2_operations = EC2Operations(region=self.__region_name)
        return ec2_operations.get_ec2_instance_list()

    def __get_grouped_ec2_instances(self, key_name: str, check_prefix: False):
        """
        This method returns the ec2 instances grouped by key_name
        :param check_prefix:
        :type check_prefix:
        :param key_name:
        :type key_name:
        :return:
        :rtype:
        """
        ec2_resources = self.__get_ec2_instances_list()
        ec2_resources_list = {}
        ec2_resource_tags = {}
        for ec2_resource in ec2_resources:
            ec2_tags = ec2_resource.get('Tags', [])
            if ec2_tags:
                groped_tag, _ = get_tag_name_and_value(tags=ec2_tags, key=key_name, check_prefix=check_prefix)
                cluster_id, _ = get_tag_name_and_value(tags=ec2_tags, key='cluster_id')
                user, user_value = get_tag_name_and_value(tags=ec2_tags, key='User')
                if groped_tag and (user_value == 'NA' or not cluster_id):
                    ec2_resources_list.setdefault(groped_tag, []).append(
                        {
                            'instance_id': ec2_resource.get('InstanceId'),
                            'launch_time': ec2_resource.get('LaunchTime'),
                        })
                    if groped_tag not in ec2_resource_tags:
                        ec2_resource_tags[groped_tag] = ec2_tags
        return {
            'resources': ec2_resources_list,
            'tags': ec2_resource_tags
        }

    def __get_ec2_cluster_resources(self):
        """
        This method returns the ec2 cluster resources
        :return:
        :rtype:
        """
        return self.__get_grouped_ec2_instances(key_name=self._cluster_prefix, check_prefix=True)

    def __tag_cluster_resources(self):
        """
        This method tag all cluster resources by using the resource group service provided by aws
        :return:
        :rtype:
        """
        updated_cluster_tags = {}
        responses = self.__get_ec2_cluster_resources()
        ec2_resources = responses.get('resources', {})
        ec2_resources_tags = responses.get('tags', {})
        if ec2_resources:
            resource_group_tag_api_operations = ResourceTagAPIOperations(region_name=self.__region_name)
            for cluster_tag, resources in ec2_resources.items():
                add_new_tags = {'cluster_id': cluster_tag.split('/')[-1], 'Budget': self._account}
                username = ''
                if resources:
                    for resource in resources:
                        instance_id = resource.get('instance_id')
                        launch_time = resource.get('launch_time')
                        # Three places we can get the username, RunInstances, StartInstances, StopInstances
                        username = self.get_username(region_name=self.__region_name, start_time=launch_time,
                                                     resource_id=instance_id, resource_type='RunInstances',
                                                     tags=ec2_resources_tags[cluster_tag])
                        if not username:
                            username = self.get_username(region_name=self.__region_name, start_time=launch_time,
                                                         resource_id=instance_id, resource_type='StartInstances',
                                                         tags=ec2_resources_tags[cluster_tag])
                        if not username:
                            username = self.get_username(region_name=self.__region_name, start_time=launch_time,
                                                         resource_id=instance_id, resource_type='StopInstances',
                                                         tags=ec2_resources_tags[cluster_tag])
                        if username:
                            break
                if username:
                    get_user_tags = self._iam_operations.get_user_tags(username=username)
                    if not get_user_tags:
                        get_user_tags = [{'Key': 'User', 'Value': username}]
                    tags_to_add = self._mandatory_tags
                    if self._tag_optional_tags:
                        tags_to_add.extend(self._optional_tags)
                    for mandatory_tag in tags_to_add:
                        _, tag_value = get_tag_name_and_value(tags=get_user_tags, key=mandatory_tag)
                        if tag_value:
                            add_new_tags.update({mandatory_tag: tag_value})
                        if mandatory_tag == 'Email' and not tag_value:
                            add_new_tags.update({mandatory_tag: f'{username}@{self._gmail_domain}'})
                else:
                    add_new_tags.update({'Key': 'User', 'Value': 'NA'})
                    add_new_tags.update(self._fill_na_tags())
                default_tags = convert_key_values_to_dict(tags=ec2_resources_tags[cluster_tag])
                updated_tags = self._get_tags_to_update(default_tags=default_tags, new_tags=add_new_tags)
                if updated_tags:
                    cluster_resources = resource_group_tag_api_operations.tag_resources_by_tag_key_value(
                        tags=updated_tags,
                        tag_key=cluster_tag,
                        dry_run=self._dry_run)
                    logger.info(f"Tags to be updated on ClusterId: {cluster_tag} are: {updated_tags} and "
                                f"the resources: {cluster_resources}")
                    updated_cluster_tags[cluster_tag] = {
                        'resources': cluster_resources,
                        'tags': updated_tags
                    }
        return updated_cluster_tags

    @logger_time_stamp
    def run(self):
        """
        This method starts the operations
        :return:
        :rtype:
        """
        logger_message = "Running the Cluster tagging in the Region"
        if self._run_active_regions:
            resources_by_region = []
            ec2_operations = EC2Operations(region='us-east-1')
            regions = ec2_operations.get_active_regions()
            for region in regions:
                self.__region_name = region
                logger.info(f"{logger_message}: {region}")
                resources_by_region.append({region: self.__tag_cluster_resources()})
        else:
            logger.info(f"{logger_message}: {self.__region_name}")
            return self.__tag_cluster_resources()
