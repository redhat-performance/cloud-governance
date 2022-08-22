import datetime
import operator

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from operator import ge


class EC2Stop(NonClusterZombiePolicy):
    """
    This class delete the stopped ec2 instance
    Send mail to the user if the ec2 instance is stopped > 20, 25th days
    Delete the instance when it stopped 30 days
    """

    FIRST_MAIL_NOTIFICATION_INSTANCE_DAYS = 20
    SECOND_MAIL_NOTIFICATION_INSTANCE_DAYS = 25
    DELETE_INSTANCE_DAYS = 30

    def __init__(self):
        super().__init__()
        self._cloudtrail = CloudTrailOperations(region_name=self._region)

    def run(self):
        """
        This method list all stopped instances for more than 30 days and terminate if dry_run no
        @return:
        """
        return self.__fetch_stop_instance(sign=ge, instance_days=self.FIRST_MAIL_NOTIFICATION_INSTANCE_DAYS, delete_instance_days=self.DELETE_INSTANCE_DAYS)

    def __fetch_stop_instance(self, instance_days: int, delete_instance_days: int, sign: operator = ge):
        """
        This method list all stopped instances for more than 30 days and terminate if dry_run no
        @return:
        """
        instances = self._ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])['Reservations']
        stopped_instances = []
        stopped_instance_tags = {}
        for instance in instances:
            for resource in instance['Instances']:
                instance_id = resource.get('InstanceId')
                stopped_time = self._cloudtrail.get_stop_time(resource_id=instance_id, event_name='StopInstances')
                if not stopped_time:
                    stopped_time = datetime.datetime.now()
                days = self._calculate_days(create_date=stopped_time)
                if days in (instance_days, self.SECOND_MAIL_NOTIFICATION_INSTANCE_DAYS):
                    user = self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='User')
                    if user:
                        self.__trigger_mail(user=user, stopped_time=stopped_time, resource_id=instance_id, days=days)
                    else:
                        logger.info('User is missing')
                if sign(days, instance_days):
                    if days >= delete_instance_days:
                        stopped_instance_tags[resource.get('InstanceId')] = resource.get('Tags')
                    stopped_instances.append([resource.get('InstanceId'), self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='Name'),
                                              self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='User'), str(resource.get('LaunchTime')),
                                              self._get_tag_name_from_tags(tags=resource.get('Tags'), tag_name='Policy')
                                              ])
        if self._dry_run == "no":
            for instance_id, tags in stopped_instance_tags.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    tags.append({'Key': 'Policy', 'Value': 'backup'})
                    tag_specifications = [{'ResourceType': 'image', 'Tags': tags}]
                    if sign == ge:
                        tag_specifications.append({'ResourceType': 'snapshot', 'Tags': tags})
                    self._ec2_client.create_image(InstanceId=instance_id, Name=self._get_tag_name_from_tags(tags=tags), TagSpecifications=tag_specifications)
                    self._ec2_client.terminate_instances(InstanceIds=[instance_id])
                    logger.info(f'Deleted the instance: {instance_id}')
        return stopped_instances

    def __trigger_mail(self, user: str, stopped_time: str, resource_id: str, days: int):
        """
        This method send triggering mail
        @param user:
        @param stopped_time:
        @param resource_id:
        @param days:
        @return:
        """
        if user in self._literal_eval():
            receivers_list = [f'{self._literal_eval()[user]}@redhat.com']
        else:
            receivers_list = [f'{user}@redhat.com']
        subject = f'Instance- {resource_id} stopped more than {days} days'
        body = f"""
Hi,

Instance: {resource_id} is stopped on {stopped_time} is stopped more than {days} days.  
After {self.DELETE_INSTANCE_DAYS} days of instance is stopped we delete that instance. Please backup your data. If you don't want to delete this instance add Policy=Not_Delete tag to your instance.
If you already added the Policy=Not_Delete tag ignore this mail.

Thanks
Thirumalesh""".strip()
        self._mail.send_mail(receivers_list=receivers_list, body=body, subject=subject)
