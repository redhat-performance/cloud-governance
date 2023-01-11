import datetime
from ast import literal_eval

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.price.resources_pricing import ResourcesPricing
from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources


class NonClusterZombiePolicy:

    DAYS_TO_DELETE_RESOURCE = 7
    DAYS_TO_NOTIFY_ADMINS = 6
    DAYS_TO_TRIGGER_RESOURCE_MAIL = 4
    DAILY_HOURS = 24

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self._end_date = datetime.datetime.now()
        self._start_date = self._end_date - datetime.timedelta(days=self.DAYS_TO_DELETE_RESOURCE)
        self._account = self.__environment_variables_dict.get('account', '')
        self._dry_run = self.__environment_variables_dict.get('dry_run', 'yes')
        self._region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._policy = self.__environment_variables_dict.get('policy', '')
        self._policy_output = self.__environment_variables_dict.get('policy_output', '')
        self._ec2_client = boto3.client('ec2', region_name=self._region)
        self._ec2_operations = EC2Operations(region=self._region)
        self._s3_client = boto3.client('s3')
        self._iam_operations = IAMOperations()
        self._iam_client = boto3.client('iam')
        self._cluster_prefix = 'kubernetes.io/cluster'
        self._zombie_cluster = ZombieClusterResources(cluster_prefix=self._cluster_prefix)
        self._s3operations = S3Operations(region_name=self._region)
        self._cloudtrail = CloudTrailOperations(region_name=self._region)
        self._special_user_mails = self.__environment_variables_dict.get('special_user_mails', '{}')
        self._account_admin = self.__environment_variables_dict.get('account_admin', '')
        self._mail = Postfix()
        self._mail_description = MailMessage()
        self.__ldap_host_name = self.__environment_variables_dict.get('LDAP_HOST_NAME', '')
        self._ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)
        self._admins = ['athiruma@redhat.com', 'ebattat@redhat.com']
        self._es_upload = ElasticUpload()
        self.resource_pricing = ResourcesPricing()

    def set_dryrun(self, value: str):
        self._dry_run = value

    def set_policy(self, value: str):
        self._policy = value

    def set_region(self, value: str):
        self._region = value

    def _literal_eval(self, data: any):
        tags = {}
        if data:
            tags = literal_eval(data)
        return tags

    def _check_cluster_tag(self, tags: list):
        """
        This method returns True if it is live cluster tag is active False not
        @param tags:
        @return:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').startswith(self._cluster_prefix):
                    return True
        return False

    def _get_tag_name_from_tags(self, tags: list, tag_name: str = 'Name'):
        """
        This method returns the tag_name from resource tags
        @param tags:
        @param tag_name:
        @return:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').strip().lower() == tag_name.lower():
                    return tag.get('Value').strip()
            return ''
        return ''

    def _calculate_days(self, create_date: datetime):
        """
        This method return the days
        @return:
        """
        today = datetime.date.today()
        days = today - create_date.date()
        return days.days

    def _get_ami_ids(self):
        """
        This method returns all image ids
        @return:
        """
        images = self._ec2_operations.get_images()
        image_ids = []
        for image in images:
            image_ids.append(image.get('ImageId'))
        return image_ids

    def _beautify_upload_data(self, upload_resource_data: list):
        """
        This method beautify the data to upload to elasticsearch
        @param upload_resource_data:
        @return:
        """
        upload_data = []
        for resource_data in upload_resource_data:
            if isinstance(resource_data, list):
                resource_str = ''
                for resource in resource_data[:-1]:
                    resource_str += f'{resource} | '
                resource_str += str(resource_data[-1])
                upload_data.append(resource_str)
            else:
                upload_data.append(resource_data)
        return upload_data

    def _get_resource_username(self, resource_id: str, resource_type: str, create_date: datetime = '', event_type: str = ''):
        """
        Get Username from the cloudtrail
        @param create_date:
        @param resource_id:
        @param resource_type:
        @return:
        """
        if event_type:
            return self._cloudtrail.get_username_by_instance_id_and_time(start_time=create_date, resource_id=resource_id,
                                                                         resource_type=resource_type, event_type=event_type)
        else:
            return self._cloudtrail.get_username_by_instance_id_and_time(start_time=create_date, resource_id=resource_id,
                                                                         resource_type=resource_type)

    def _get_policy_value(self, tags: list):
        """
        This method beautify the value
        @param tags:
        @return:
        """
        policy_value = self._get_tag_name_from_tags(tags=tags, tag_name='Policy').strip()
        if policy_value:
            return policy_value.replace('_', '').replace('-', '').upper()
        return 'NA'

    def _trigger_mail(self, tags: list, resource_id: str, days: int, resource_type: str, **kwargs):
        """
        This method send triggering mail
        @param tags:
        @param resource_id:
        @return:
        """
        try:
            special_user_mails = self._literal_eval(self._special_user_mails)
            user, resource_name = self._get_tag_name_from_tags(tags=tags, tag_name='User'), self._get_tag_name_from_tags(
                tags=tags, tag_name='Name')
            if not resource_name:
                resource_name = self._get_tag_name_from_tags(tags=tags, tag_name='cg-Name')
            to = user if user not in special_user_mails else special_user_mails[user]
            ldap_data = self._ldap.get_user_details(user_name=to)
            cc = [self._account_admin, f'{ldap_data.get("managerId")}@redhat.com']
            name = to
            if ldap_data:
                name = ldap_data.get('displayName')
            subject, body = self._mail_description.resource_message(name=name, days=days,
                                                                    notification_days=self.DAYS_TO_TRIGGER_RESOURCE_MAIL,
                                                                    delete_days=self.DAYS_TO_DELETE_RESOURCE,
                                                                    resource_name=resource_name, resource_id=resource_id,
                                                                    resource_type=resource_type, msgadmins=self.DAYS_TO_NOTIFY_ADMINS, extra_purse=kwargs.get('extra_purse'))
            if not kwargs.get('admins'):
                self._mail.send_email_postfix(to=to, content=body, subject=subject, cc=cc, resource_id=resource_id, message_type=kwargs.get('message_type'), extra_purse=kwargs.get('delta_cost', 0))
            else:
                kwargs['admins'].append(f'{ldap_data.get("managerId")}@redhat.com')
                self._mail.send_email_postfix(to=kwargs.get('admins'), content=body, subject=subject, cc=[], resource_id=resource_id, message_type=kwargs.get('message_type'), extra_purse=kwargs.get('delta_cost', 0))
        except Exception as err:
            logger.info(err)

    def _update_tag_value(self, tags: list, tag_name: str, tag_value: str):
        """
        This method updates the tag value
        @param tags:
        @param tag_name:
        @param tag_value:
        @return:
        """
        found = False
        if tags:
            for tag in tags:
                if tag.get('Key') == tag_name:
                    tag['Value'] = str(tag_value)
                    found = True
            if not found:
                tags.append({'Key': tag_name, 'Value': str(tag_value)})
            return tags
        return [{'Key': tag_name, 'Value': str(tag_value)}]

    def _get_resource_last_used_days(self, tags: list):
        """
        This method get last used day from the tags
        @param tags:
        @return:
        """
        last_used_day = self._get_tag_name_from_tags(tags=tags, tag_name='LastUsedDay')
        if not last_used_day:
            last_used_day = 1
        else:
            last_used_day = int(last_used_day) + 1
        return last_used_day

    def __delete_resource_on_name(self, resource_id: str):
        try:
            if self._policy == 's3_inactive':
                self._s3_client.delete_bucket(Bucket=resource_id)
            elif self._policy == 'empty_roles':
                self._iam_client.delete_role(RoleName=resource_id)
            elif self._policy == 'ebs_unattached':
                self._ec2_client.delete_volume(VolumeId=resource_id)
            elif self._policy == 'ip_unattached':
                self._ec2_client.release_address(AllocationId=resource_id)
            elif self._policy == 'nat_gateway_unused':
                self._ec2_client.delete_nat_gateway(NatGatewayId=resource_id)
            elif self._policy == 'zombie_snapshots':
                self._ec2_client.delete_snapshot(SnapshotId=resource_id)
            logger.info(f'{self._policy} deleted: {resource_id}')
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def _check_resource_and_delete(self, resource_name: str, resource_id: str, resource_type: str, resource: dict, empty_days: int, days_to_delete_resource: int, tags: list = [], **kwargs):
        """
        This method check and delete resources
        @param resource_name:
        @param resource_id:
        @param resource_type:
        @param resource:
        @param empty_days:
        @param days_to_delete_resource:
        @param tags:
        @return:
        """
        resource_id = resource.get(resource_id)
        if not tags:
            tags = resource.get('Tags') if resource.get('Tags') else []
        user = self._get_tag_name_from_tags(tag_name='User', tags=tags)
        if not user:
            user = self._get_resource_username(resource_id=resource_id, resource_type=resource_type, event_type='EventName')
            if user:
                tags.append({'Key': 'User', 'Value': user})
        zombie_resource = {}
        if empty_days >= self.DAYS_TO_TRIGGER_RESOURCE_MAIL:
            if empty_days == self.DAYS_TO_TRIGGER_RESOURCE_MAIL:
                kwargs['delta_cost'] = kwargs.get('extra_purse')
                self._trigger_mail(resource_type=resource_name, resource_id=resource_id, tags=tags, days=self.DAYS_TO_TRIGGER_RESOURCE_MAIL, message_type='notification', extra_purse=kwargs.get('extra_purse'), delta_cost=kwargs.get('delta_cost', 0))
            elif empty_days == self.DAYS_TO_NOTIFY_ADMINS:
                self._trigger_mail(resource_type=resource_name, resource_id=resource_id, tags=tags, days=empty_days, admins=self._admins, message_type='notify_admin', extra_purse=kwargs.get('extra_purse'), delta_cost=kwargs.get('delta_cost', 0))
            elif empty_days >= days_to_delete_resource:
                if self._dry_run == 'no':
                    if self._get_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                        self._trigger_mail(resource_type=resource_name, resource_id=resource_id, tags=tags, days=empty_days, message_type='delete', extra_purse=kwargs.get('extra_purse'), delta_cost=kwargs.get('delta_cost', 0))
                        self.__delete_resource_on_name(resource_id=resource_id)
            zombie_resource = resource
        return zombie_resource

    def _update_resource_tags(self, resource_id: str, left_out_days: int, tags: list, resource_left_out: bool):
        """
        This method update the tags in aws
        @return:
        """
        if left_out_days < 7 or self._dry_run == 'yes' or self._get_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
            if self._get_tag_name_from_tags(tags=tags, tag_name='LastUsedDay') or resource_left_out:
                tags = self._update_tag_value(tags=tags, tag_name='LastUsedDay', tag_value=str(left_out_days))
                try:
                    if self._policy == 's3_inactive':
                        self._s3_client.put_bucket_tagging(Bucket=resource_id, Tagging={'TagSet': tags})
                    elif self._policy == 'empty_roles':
                        self._iam_client.tag_role(RoleName=resource_id, Tags=tags)
                    elif self._policy in ('ip_unattached', 'nat_gateway_unused', 'zombie_snapshots'):
                        self._ec2_client.create_tags(Resources=[resource_id], Tags=tags)
                except Exception as err:
                    logger.info(f'Exception raised: {err}: {resource_id}')

    def _organise_instance_data(self, resources: list):
        """
        This method convert all datetime into string
        @param resources:
        @return:
        """
        organize_data = []
        if 'ec2' in self._policy:
            for instance in resources:
                instance['LaunchTime'] = instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                for index, device_mappings in enumerate(instance['BlockDeviceMappings']):
                    instance['BlockDeviceMappings'][index]['Ebs']['AttachTime'] = device_mappings['Ebs']['AttachTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                for index, network_interface in enumerate(instance['NetworkInterfaces']):
                    instance['NetworkInterfaces'][index]['Attachment']['AttachTime'] = network_interface['Attachment']['AttachTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                if instance.get('UsageOperationUpdateTime'):
                    instance['UsageOperationUpdateTime'] = instance['UsageOperationUpdateTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                if instance.get('metrics'):
                    for index, metric in enumerate(instance['metrics']):
                        instance['metrics'][index]['Timestamps'] = [date.strftime("%Y-%m-%dT%H:%M:%S+00:00") for date in metric['Timestamps']]
                organize_data.append(instance)
        else:
            for volume in resources:
                if volume.get('Attachments'):
                    for attachment in volume.get('Attachments'):
                        attachment['AttachTime'] = attachment['AttachTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                volume['CreateTime'] = volume['CreateTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00")
                organize_data.append(volume)
        return organize_data

    def get_ebs_cost(self, resource: any, resource_type: str, resource_hours: int):
        ebs_cost = 0
        if resource_type == 'ec2':
            volume_ids = []
            for block_device in resource:
                volume_ids.append(block_device.get('Ebs').get('VolumeId'))
            volumes = self._ec2_client.describe_volumes(VolumeIds=volume_ids)['Volumes']
            for volume in volumes:
                ebs_cost += self.resource_pricing.get_ebs_cost(volume_size=volume.get('Size'), volume_type=volume.get('VolumeType'), hours=resource_hours)
        else:
            if resource_type == 'ebs':
                ebs_cost += self.resource_pricing.get_ebs_cost(volume_size=resource.get('Size'), volume_type=resource.get('VolumeType'), hours=resource_hours)
        return round(ebs_cost, 3)
