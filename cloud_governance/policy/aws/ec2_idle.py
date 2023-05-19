from datetime import datetime, timedelta

from cloud_governance.common.clouds.aws.cloudwatch.cloudwatch_operations import CloudWatchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EC2Idle(NonClusterZombiePolicy):
    """
    This class stop the idle ec2 instances more than 4 days if the matches the required metrics
    CpuUtilization < 2 percent
    NetworkIN < 5k bytes
    NetworkOut < 5k bytes
    We trigger email if the ec2 instance is idle 2 days and stop the instance if it is idle 4 days
    """

    INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS = 4
    STOP_INSTANCE_IDLE_DAYS = 7
    CPU_UTILIZATION_PERCENTAGE = 2
    NETWORK_IN_BYTES = 5000
    NETWORK_OUT_BYTES = 5000
    INSTANCE_LAUNCH_DAYS = 7

    def __init__(self):
        super().__init__()
        self._cloudwatch = CloudWatchOperations(region=self._region)

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
        ec2_idle_cost = {}
        block_device_mappings = {}
        ec2_types = {}
        for instance in instances:
            for resource in instance['Instances']:
                if self._get_policy_value(tags=resource.get('Tags', [])) not in ('NOTDELETE', 'SKIP') and not self._check_cluster_tag(tags=resource.get('Tags', [])):
                    launch_days = self.__get_time_difference(launch_time=resource.get('LaunchTime'))
                    if launch_days >= instance_launch_days:
                        instance_id = resource.get('InstanceId')
                        metrics_4_days = self.__get_metrics_from_cloud_watch(instance_id=instance_id, instance_period=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS)
                        cpu_metric_4_days, network_in_4_days, network_out_2_days = self.__get_proposed_metrics(metrics=metrics_4_days, metric_period=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS)
                        if cpu_metric_4_days < self.CPU_UTILIZATION_PERCENTAGE and network_in_4_days < self.NETWORK_IN_BYTES and network_out_2_days < self.NETWORK_OUT_BYTES:
                            if not self._ec2_operations.is_cluster_resource(resource_id=instance_id):
                                resource['metrics'] = metrics_4_days
                                running_idle_instances[instance_id] = resource
                            user = self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='User')
                            if user:
                                idle_cost = self.resource_pricing.ec2_instance_type_cost(instance_type=resource.get('InstanceType'), hours=(self.DAILY_HOURS*self.DAYS_TO_TRIGGER_RESOURCE_MAIL))
                                idle_ebs_cost = self.get_ebs_cost(resource=resource.get('BlockDeviceMappings'), resource_type='ec2', resource_hours=(self.DAILY_HOURS * self.DAYS_TO_TRIGGER_RESOURCE_MAIL))
                                self.__trigger_mail(tags=resource.get('Tags'), resource_id=instance_id, days=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS, ec2_type=resource.get('InstanceType'),
                                                    instance_id=instance_id, message_type='notification', extra_purse=(idle_cost+idle_ebs_cost), delta_cost=(idle_cost+idle_ebs_cost))
                            else:
                                logger.info('User is missing')
                        if not self._ec2_operations.is_cluster_resource(resource_id=instance_id):
                            metrics_7_days = self.__get_metrics_from_cloud_watch(instance_id=instance_id, instance_period=self.STOP_INSTANCE_IDLE_DAYS)
                            cpu_metric_7_days, network_in_7_days, network_out_7_days = self.__get_proposed_metrics(metrics=metrics_4_days, metric_period=self.STOP_INSTANCE_IDLE_DAYS)
                            if cpu_metric_7_days < self.CPU_UTILIZATION_PERCENTAGE and network_in_4_days < self.NETWORK_IN_BYTES and network_out_7_days < self.NETWORK_OUT_BYTES:
                                resource['metrics'] = metrics_7_days
                                idle_cost = self.resource_pricing.ec2_instance_type_cost(
                                    instance_type=resource.get('InstanceType'),
                                    hours=(self.DAILY_HOURS * self.DAYS_TO_TRIGGER_RESOURCE_MAIL))
                                idle_ebs_cost = self.get_ebs_cost(resource=resource.get('BlockDeviceMappings'), resource_type='ec2', resource_hours=(self.DAILY_HOURS * self.DAYS_TO_TRIGGER_RESOURCE_MAIL))
                                ec2_idle_cost[instance_id] = idle_ebs_cost + idle_cost
                                block_device_mappings[instance_id] = resource.get('BlockDeviceMappings')
                                running_idle_instances[instance_id] = resource
                                running_instance_tags[instance_id] = resource.get('Tags')
                                ec2_types[instance_id] = resource.get('InstanceType')
        if self._dry_run == "no":
            for instance_id, tags in running_instance_tags.items():
                if self._get_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                    self._ec2_client.stop_instances(InstanceIds=[instance_id])
                    logger.info(f'Stopped the instance: {instance_id}')
                    idle_cost = self.resource_pricing.ec2_instance_type_cost(instance_type=ec2_types[instance_id], hours=(self.DAILY_HOURS * self.DAYS_TO_DELETE_RESOURCE))
                    idle_ebs_cost = self.get_ebs_cost(resource=block_device_mappings[instance_id], resource_type='ec2', resource_hours=(self.DAILY_HOURS * self.DAYS_TO_DELETE_RESOURCE))
                    self.__trigger_mail(tags=tags, resource_id=instance_id, days=self.STOP_INSTANCE_IDLE_DAYS, ec2_type=ec2_types[instance_id], instance_id=instance_id, message_type='delete', extra_purse=(idle_ebs_cost+idle_cost), delta_cost=ec2_idle_cost[instance_id])
        return self._organise_instance_data(list(running_idle_instances.values()))

    def __get_metrics_average(self, metric_list: list, metric_period: int):
        """
        This method calculate the average of the metrics
        @param metric_list:
        @param metric_period:
        @return:
        """
        metrics = []
        for metric in metric_list:
            metrics.append(sum(metric['Values']) / metric_period)
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
        This method returns the metrics
        @param metrics:
        @param metric_period:
        @return:
        """
        return self.__get_metrics_average(metric_list=metrics, metric_period=metric_period)

    def __get_time_difference(self, launch_time: datetime):
        """
        This method returns the difference of datetime
        @param launch_time:
        @return:
        """
        end_time = datetime.now()
        return (end_time - launch_time.replace(tzinfo=None)).days

    def __trigger_mail(self, tags: list, resource_id: str, days: int, ec2_type: str = '', instance_id: str = '', **kwargs):
        """
        This method send triggering mail
        @param tags:
        @param resource_id:
        @return:
        """
        try:
            special_user_mails = self._literal_eval(self._special_user_mails)
            user, instance_name = self._get_tag_name_from_tags(tags=tags, tag_name='User'), self._get_tag_name_from_tags(tags=tags, tag_name='Name')
            to = user if user not in special_user_mails else special_user_mails[user]
            ldap_data = self._ldap.get_user_details(user_name=to)
            cc = [self._account_admin, f'{ldap_data.get("managerId")}@redhat.com']
            subject, body = self._mail_description.ec2_idle(name=ldap_data.get('displayName'), days=days, notification_days=self.INSTANCE_IDLE_MAIL_NOTIFICATION_DAYS, stop_days=self.STOP_INSTANCE_IDLE_DAYS, instance_name=instance_name, resource_id=resource_id, ec2_type=ec2_type, extra_purse=kwargs.get('extra_purse'))
            self._mail.send_email_postfix(to=to, content=body, subject=subject, cc=cc, resource_id=instance_id, message_type=kwargs.get('message_type'), extra_purse=kwargs.get('delta_cost', 0))
        except Exception as err:
            logger.info(err)
