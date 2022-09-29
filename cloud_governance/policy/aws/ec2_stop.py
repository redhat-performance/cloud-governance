import datetime
import operator

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
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
        stopped_time = ''
        days = 0
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
                        self.__trigger_mail(tags=resource.get('Tags'), stopped_time=stopped_time, resource_id=instance_id, days=days)
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
                    try:
                        ami_id = self._ec2_client.create_image(InstanceId=instance_id, Name=self._get_tag_name_from_tags(tags=tags), TagSpecifications=tag_specifications)['ImageId']
                        self.__trigger_mail(tags=tags, stopped_time=stopped_time, days=days, resource_id=instance_id, image_id=ami_id)
                        self._ec2_client.terminate_instances(InstanceIds=[instance_id])
                        logger.info(f'Deleted the instance: {instance_id}')
                    except Exception as err:
                        logger.info(err)
        return stopped_instances

    def __trigger_mail(self, tags: list, stopped_time: str, resource_id: str, days: int, image_id: str = ''):
        """
        This method send triggering mail
        @param tags:
        @param stopped_time:
        @param resource_id:
        @param days:
        @return:
        """
        try:
            special_user_mails = self._literal_eval(self._special_user_mails)
            user, instance_name = self._get_tag_name_from_tags(tags=tags, tag_name='User'), self._get_tag_name_from_tags(tags=tags, tag_name='Name')
            to = user if user not in special_user_mails else special_user_mails[user]
            ldap_data = self._ldap.get_user_details(user_name=to)
            cc = [self._account_admin, f'{ldap_data.get("managerId")}@redhat.com']
            subject, body = self._mail_description.ec2_stop(name=ldap_data.get('displayName'), days=days, image_id=image_id, delete_instance_days=self.DELETE_INSTANCE_DAYS, instance_name=instance_name, resource_id=resource_id, stopped_time=stopped_time)
            self._mail.send_email_postfix(to=to, content=body, subject=subject, cc=cc)
        except Exception as err:
            logger.info(err)
