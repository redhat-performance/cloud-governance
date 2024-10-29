from cloud_governance.common.clouds.aws.cloudwatch.cloudwatch_operations import CloudWatchOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.price.resources_pricing import ResourcesPricing
from cloud_governance.common.clouds.aws.rds.rds_operations import RDSOperations
from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.utils.configs import INSTANCE_IDLE_DAYS, DEFAULT_ROUND_DIGITS, TOTAL_BYTES_IN_KIB, \
    EC2_NAMESPACE, CLOUDWATCH_METRICS_AVAILABLE_DAYS
from cloud_governance.common.utils.utils import Utils
from cloud_governance.policy.helpers.abstract_policy_operations import AbstractPolicyOperations
from cloud_governance.common.logger.init_logger import logger


class AWSPolicyOperations(AbstractPolicyOperations):

    def __init__(self):
        super().__init__()
        self._region = self._environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._cloud_name = 'AWS'
        self._ec2_client = get_boto3_client(client='ec2', region_name=self._region)
        self._s3_client = get_boto3_client('s3', region_name=self._region)
        self._iam_operations = IAMOperations()
        self._rds_operations = RDSOperations(region_name=self._region)
        self._s3operations = S3Operations(region_name=self._region)
        self._ec2_operations = EC2Operations(region=self._region)
        self._cloudwatch = CloudWatchOperations(region=self._region)
        self._resource_pricing = ResourcesPricing()
        self.cost_savings_tag = [{'Key': 'cost-savings', 'Value': 'true'}]

    def get_tag_name_from_tags(self, tags: list, tag_name: str) -> str:
        """
        This method returns the tag value from the tags
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :return:
        :rtype:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').strip().lower() == tag_name.lower():
                    return tag.get('Value').strip()
        return ''

    def _delete_resource(self, resource_id: str):
        """
        This method deletes the resource by verifying the policy
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        action = "deleted"
        try:
            if self._policy == 's3_inactive':
                self._s3_client.delete_bucket(Bucket=resource_id)
            elif self._policy == 'empty_roles':
                response = self._iam_operations.delete_role(role_name=resource_id)
            elif self._policy == 'unattached_volume':
                self._ec2_client.delete_volume(VolumeId=resource_id)
            elif self._policy == 'ip_unattached':
                self._ec2_client.release_address(AllocationId=resource_id)
            elif self._policy == 'unused_nat_gateway':
                self._ec2_client.delete_nat_gateway(NatGatewayId=resource_id)
            elif self._policy == 'zombie_snapshots':
                self._ec2_client.delete_snapshot(SnapshotId=resource_id)
            elif self._policy == 'instance_run':
                self._ec2_client.stop_instances(InstanceIds=[resource_id])
                action = "Stopped"
            elif self._policy == 'database_idle':
                # @ Todo add the delete method after successful monitoring
                return False
            logger.info(f'{self._policy} {action}: {resource_id}')
        except Exception as err:
            logger.error(f'Exception raised: {err}: {resource_id}')
            raise err

    def __remove_tag_key_aws(self, tags: list):
        """
        This method returns the tags that does not contain key startswith aws:
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        custom_tags = []
        for tag in tags:
            if not tag.get('Key').lower().startswith('aws'):
                custom_tags.append(tag)
        return custom_tags

    def _update_tag_value(self, tags: list, tag_name: str, tag_value: str):
        """
        This method returns the updated tag_list by adding the tag_name and tag_value to the tags
        @param tags:
        @param tag_name:
        @param tag_value:
        @return:
        """
        if self._dry_run == "yes":
            tag_value = 0
        tag_value = f'{self.CURRENT_DATE}@{tag_value}'
        found = False
        if tags:
            for tag in tags:
                if tag.get('Key') == tag_name:
                    if tag.get('Value').split("@")[0] != self.CURRENT_DATE:
                        tag['Value'] = tag_value
                    else:
                        if int(tag_value.split("@")[-1]) == 0 or int(tag_value.split("@")[-1]) == 1:
                            tag['Value'] = tag_value
                    found = True
        if not found:
            tags.append({'Key': tag_name, 'Value': tag_value})
        tags = self.__remove_tag_key_aws(tags=tags)
        return tags

    def delete_resource_tags(self, tags: list, resource_id: str):
        """
        This method deletes the tag of a resource
        :param tags:
        :param resource_id:
        :return:
        """
        try:
            if self._policy == 'empty_roles':
                self._iam_operations.untag_role(role_name=resource_id, tags=tags)
            elif self._policy in ('ip_unattached', 'unused_nat_gateway', 'zombie_snapshots', 'unattached_volume',
                                  'instance_run', 'instance_idle'):
                self._ec2_client.delete_tags(Resources=[resource_id], Tags=tags)
            elif self._policy == 'database_idle':
                self._rds_operations.remove_tags_from_resource(resource_arn=resource_id, tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def update_resource_tags(self, tags: list, resource_id: str):
        """
        This method updates the tags of the resource
        :param tags:
        :param resource_id:
        :return:
        """
        try:
            if self._policy == 's3_inactive':
                self._s3_client.put_bucket_tagging(Bucket=resource_id, Tagging={'TagSet': tags})
            elif self._policy == 'empty_roles':
                self._iam_operations.tag_role(role_name=resource_id, tags=tags)
            elif self._policy in ('ip_unattached', 'unused_nat_gateway', 'zombie_snapshots', 'unattached_volume',
                                  'instance_run', 'instance_idle'):
                self._ec2_client.create_tags(Resources=[resource_id], Tags=tags)
            elif self._policy == 'database_idle':
                self._rds_operations.add_tags_to_resource(resource_arn=resource_id, tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def update_resource_day_count_tag(self, resource_id: str, cleanup_days: int, tags: list,
                                      force_tag_update: str = ''):
        """
        This method updates the resource tags
        :param force_tag_update:
        :type force_tag_update:
        :param tags:
        :type tags:
        :param cleanup_days:
        :type cleanup_days:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        tags = self._update_tag_value(tags=tags, tag_name='DaysCount', tag_value=str(cleanup_days))
        self.update_resource_tags(tags=tags, resource_id=resource_id)

    def _get_all_instances(self):
        """
        This method updates the instance type count to the elasticsearch
        :return:
        :rtype:
        """
        instances = self._ec2_operations.get_ec2_instance_list()
        return instances

    def run_policy_operations(self):
        raise NotImplementedError("This method needs to be implemented")

    def _get_all_volumes(self, **kwargs) -> list:
        """
        This method returns the all volumes
        :return:
        :rtype:
        """
        volumes = self._ec2_operations.get_volumes(**kwargs)
        return volumes

    def _get_active_cluster_ids(self):
        """
        This method returns the active cluster id's
        :return:
        :rtype:
        """
        active_instances = self._ec2_operations.get_ec2_instance_list()
        cluster_ids = []
        for instance in active_instances:
            for tag in instance.get('Tags', []):
                if tag.get('Key', '').startswith('kubernetes.io/cluster'):
                    cluster_ids.append(tag.get('Key'))
                    break
        return cluster_ids

    def _get_global_active_cluster_ids(self):
        """
        This method returns the global active cluster ids
        :return:
        """
        cluster_ids = []
        active_regions = self._ec2_operations.get_active_regions()
        for region in active_regions:
            active_instances = self._ec2_operations.get_ec2_instance_list(
                ec2_client=get_boto3_client('ec2', region_name=region))
            for instance in active_instances:
                for tag in instance.get('Tags', []):
                    if tag.get('Key', '').startswith('kubernetes.io/cluster'):
                        cluster_ids.append(tag.get('Key'))
                        break
        return cluster_ids

    def _get_cluster_tag(self, tags: list):
        """
        This method returns the cluster_tag
        :return:
        :rtype:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').startswith('kubernetes.io/cluster'):
                    return tag.get('Key')
        return ''

    def __get_aggregation_metrics_value(self, metrics: list, aggregation: str):
        """
        This method calculate the average of the metrics
        @param metrics:
        @param aggregation:
        @return:
        """
        metrics_result = 0
        for metric in metrics:
            metrics_values_sum = sum(metric['Values'])
            if Utils.equal_ignore_case(aggregation, 'average'):
                metrics_result += metrics_values_sum / len(metric['Values'])
            elif Utils.equal_ignore_case(aggregation, 'sum'):
                metrics_result += metrics_values_sum
        return round(metrics_result, DEFAULT_ROUND_DIGITS)

    def get_cpu_utilization_percentage_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS, **kwargs):
        """
        This method returns the average cpu utilization percentage
        :param resource_id:
        :type resource_id:
        :param days:
        :type days:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        metrics = self._cloudwatch.get_metric_data(start_time=start_date, end_time=end_date, resource_id=resource_id,
                                                   resource_type='InstanceId', namespace=EC2_NAMESPACE,
                                                   metric_names={'CPUUtilization': 'Percent'},
                                                   statistic='Average')
        average_cpu_metrics_value = self.__get_aggregation_metrics_value(metrics.get('MetricDataResults', []),
                                                                         aggregation='average')
        return average_cpu_metrics_value

    def get_network_in_kib_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS, **kwargs):
        """
        This method returns the average network in bytes in KiB
        :param resource_id:
        :type resource_id:
        :param days:
        :type days:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        metrics = self._cloudwatch.get_metric_data(start_time=start_date, end_time=end_date, resource_id=resource_id,
                                                   resource_type='InstanceId', namespace=EC2_NAMESPACE,
                                                   metric_names={'NetworkIn': 'Bytes'},
                                                   statistic='Average')
        average_network_in_bytes = self.__get_aggregation_metrics_value(metrics.get('MetricDataResults', []),
                                                                        aggregation='average')
        return round(average_network_in_bytes / TOTAL_BYTES_IN_KIB, DEFAULT_ROUND_DIGITS)

    def get_network_out_kib_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS, **kwargs):
        """
        This method returns the average network out bytes in KiB
        :param resource_id:
        :type resource_id:
        :param days:
        :type days:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        metrics = self._cloudwatch.get_metric_data(start_time=start_date, end_time=end_date, resource_id=resource_id,
                                                   resource_type='InstanceId', namespace=EC2_NAMESPACE,
                                                   metric_names={'NetworkOut': 'Bytes'},
                                                   statistic='Average')
        average_network_out_bytes = self.__get_aggregation_metrics_value(metrics.get('MetricDataResults', []),
                                                                         aggregation='average')
        return round(average_network_out_bytes / TOTAL_BYTES_IN_KIB, DEFAULT_ROUND_DIGITS)

    def _get_ami_ids(self, **kwargs):
        """
        This method returns all image ids
        @return:
        """
        images = self._ec2_operations.get_images(**kwargs)
        image_ids = []
        for image in images:
            image_ids.append(image.get('ImageId'))
        return image_ids

    def __get_db_connection_status(self, resource_id: str, days: int = CLOUDWATCH_METRICS_AVAILABLE_DAYS):
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        metrics = self._cloudwatch.get_metric_data(resource_id=resource_id, start_time=start_date, end_time=end_date,
                                                   resource_type='DBInstanceIdentifier',
                                                   metric_names={'DatabaseConnections': 'Count'},
                                                   namespace='AWS/RDS', statistic='Maximum'
                                                   )
        total_connections = self.__get_aggregation_metrics_value(metrics.get('MetricDataResults', []),
                                                                 aggregation='sum')
        return total_connections

    def is_database_idle(self, resource_id: str):
        """
        This method returns bool on verifying the database connections
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        total_connections = self.__get_db_connection_status(resource_id)
        return int(total_connections) == 0
