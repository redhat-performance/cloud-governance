from datetime import datetime, timedelta

from cloud_governance.common.aws.cloudwatch.cloudwatch_operations import CloudWatchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EC2Idle(NonClusterZombiePolicy):
    """
    This class stop the idle ec2 instances more than 4 days if the matches the required metrics
    CpuUtilization < 2 percent
    NetworkIN < 5k bytes
    NetworkOut < 5k bytes
    We trigger email if the ec2 instance is idle 2 days and stop the instance if it is idle 4 days
    """

    INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS = 2
    STOP_INSTANCE_IDLE_DAYS = 4
    CPU_UTILIZATION_PERCENTAGE = 2
    NETWORK_IN_BYTES = 5000
    NETWORK_OUT_BYTES = 5000
    INSTANCE_LAUNCH_DAYS = 4

    def __init__(self):
        super().__init__()
        self._cloudwatch = CloudWatchOperations(region=self._region)

    def __organise_instance_data(self, instances_data: list):
        """
        This method convert all datetime into string
        @param instances_data:
        @return:
        """
        organize_data = []
        for instance in instances_data:
            instance['LaunchTime'] = instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
            for index, device_mappings in enumerate(instance['BlockDeviceMappings']):
                instance['BlockDeviceMappings'][index]['Ebs']['AttachTime'] = device_mappings['Ebs']['AttachTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
            for index, network_interface in enumerate(instance['NetworkInterfaces']):
                instance['NetworkInterfaces'][index]['Attachment']['AttachTime'] = network_interface['Attachment']['AttachTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
            if instance.get('UsageOperationUpdateTime'):
                instance['UsageOperationUpdateTime'] = instance['UsageOperationUpdateTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
            for index, metric in enumerate(instance['metrics']):
                instance['metrics'][index]['Timestamps'] = [date.strftime("%Y-%m-%dT%H:%M:%S+00:00") for date in metric['Timestamps']]
            organize_data.append(instance)
        return organize_data

    def run(self):
        """
        This method list all idle instances and stop if it is idle since 4 days
        @return:
        """
        return self.__stop_idle_instances(instance_launch_days=self.INSTANCE_LAUNCH_DAYS)

    def __stop_idle_instances(self, instance_launch_days: int):
        """
        This method list all idle instances and stop  if it s idle since 4 days
        @param instance_launch_days:
        @return:
        """
        instances = self._ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])['Reservations']
        running_idle_instances = {}
        running_instance_tags = {}
        for instance in instances:
            for resource in instance['Instances']:
                launch_days = self.__get_time_difference(launch_time=resource.get('LaunchTime'))
                if launch_days > instance_launch_days:
                    instance_id = resource.get('InstanceId')
                    metrics_2_days = self.__get_metrics_from_cloud_watch(instance_id=instance_id, instance_period=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS)
                    cpu_metric_2_days, network_in_2_days, network_out_2_days = self.__get_proposed_metrics(metrics=metrics_2_days, metric_period=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS)
                    if cpu_metric_2_days < self.CPU_UTILIZATION_PERCENTAGE and network_in_2_days < self.NETWORK_IN_BYTES and network_out_2_days < self.NETWORK_OUT_BYTES:
                        if not self._ec2_operations.is_cluster_resource(resource_id=instance_id):
                            resource['metrics'] = metrics_2_days
                            running_idle_instances[instance_id] = resource
                        user = self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='User')
                        if user:
                            resource_metrics = [str(cpu_metric_2_days), str(network_in_2_days), str(network_out_2_days)]
                            self.__trigger_mail(user=user, resource_id=instance_id, metrics=resource_metrics)
                        else:
                            logger.info('User is missing')
                    if not self._ec2_operations.is_cluster_resource(resource_id=instance_id):
                        metrics_4_days = self.__get_metrics_from_cloud_watch(instance_id=instance_id, instance_period=self.STOP_INSTANCE_IDLE_DAYS)
                        cpu_metric_4_days, network_in_4_days, network_out_4_days = self.__get_proposed_metrics(metrics=metrics_4_days, metric_period=self.STOP_INSTANCE_IDLE_DAYS)
                        if cpu_metric_4_days < self.CPU_UTILIZATION_PERCENTAGE and network_in_4_days < self.NETWORK_IN_BYTES and network_out_4_days < self.NETWORK_OUT_BYTES:
                            resource['metrics'] = metrics_4_days
                            running_idle_instances[instance_id] = resource
                            running_instance_tags[instance_id] = resource.get('Tags')
        if self._dry_run == "no":
            for instance_id, tags in running_instance_tags.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    self._ec2_client.stop_instances(InstanceIds=[instance_id])
                    logger.info(f'Stopped the instance: {instance_id}')
        return self.__organise_instance_data(list(running_idle_instances.values()))

    def __get_metrics_average(self, metric_list: list, metric_period: int):
        """
        This method calculate the average of the metrics
        @param metric_list:
        @param metric_period:
        @return:
        """
        metrics = []
        for metric in metric_list:
            metrics.append(sum(metric['Values'])/metric_period)
        return metrics

    def __get_metrics_from_cloud_watch(self, instance_id: str, instance_period: int):
        """
        This method extracts the logs from the cloudwatch
        @param instance_id:
        @param instance_period:
        @return:
        """
        start_time, end_time = datetime.now() - timedelta(days=instance_period), datetime.now()
        metrics = self._cloudwatch.get_metric_data(start_time=start_time, end_time=end_time, resource_id=instance_id,
                                                   resource_type='InstanceId', namespace='AWS/EC2',
                                                   metric_names={'CPUUtilization': 'Percent', 'NetworkIn': 'Bytes', 'NetworkOut': 'Bytes'},
                                                   statistic='Average')
        return metrics['MetricDataResults']

    def __get_proposed_metrics(self, metrics: list, metric_period: int):
        """
        This method return the metrics
        @param metrics:
        @param metric_period:
        @return:
        """
        return self.__get_metrics_average(metric_list=metrics, metric_period=metric_period)

    def __get_time_difference(self, launch_time: datetime):
        """
        This method return the difference of datetime
        @param launch_time:
        @return:
        """
        end_time = datetime.now()
        return (end_time - launch_time.replace(tzinfo=None)).days

    def __trigger_mail(self, user: str, resource_id: str, metrics: list):
        """
        This method send triggering mail
        @param user:
        @param resource_id:
        @return:
        """
        if user in self._literal_eval():
            receivers_list = [f'{self._literal_eval()[user]}@redhat.com']
        else:
            receivers_list = [f'{user}@redhat.com']
        subject = f'Instance- {resource_id} idle more than {self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS} days'
        body = f"""
Hi,

Instance: {resource_id} is idle since {self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS}.  
After {self.STOP_INSTANCE_IDLE_DAYS} days of instance is idle we stop that instance. If you don't want to stop this instance add Policy=Not_Delete tag to your instance. 
If you already added the Policy=Not_Delete tag ignore this mail.
FYI, Here the Average of {self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS} days of metrics:
CpuUtilization, NetworkIn, NwtworkOut
{", ".join(metrics)}

Thanks
Thirumalesh""".strip()
        self._mail.send_mail(receivers_list=receivers_list, body=body, subject=subject)
