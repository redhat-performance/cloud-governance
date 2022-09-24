from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.utils import Utils


class NonClusterOperations:

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes', input_tags: dict = ''):
        self.region = region
        self.dry_run = dry_run
        self.input_tags = input_tags
        self.cloudtrail = boto3.client('cloudtrail', region_name=region)
        self.cluster_prefix = 'kubernetes.io/cluster/'
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cloudtrail = CloudTrailOperations(region_name=self.region)
        self.iam_client = IAMOperations()
        self.ec2_operations = EC2Operations(region=region)
        self.utils = Utils(region=region)

    def _get_instances_data(self, instance_id: str = ''):
        """
        This method go over all instances
        :return:
        """
        ec2s_data = self.ec2_operations.get_instances()
        if instance_id:
            for items in ec2s_data:
                if items.get('Instances'):
                    for item in items['Instances']:
                        if item.get('InstanceId') == instance_id:
                            return items['Instances']
        else:
            instances_list = []
            for items in ec2s_data:
                if items.get('Instances'):
                    instances_list.append(items['Instances'])
            return instances_list

    def _append_input_tags(self):
        """
        This method build tags list according to input tags dictionary
        @return:
        """
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def _get_tags_of_resources(self, tags: list, search_tags: list):
        """
        This method extracts tags from the resource tags
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

    def _fill_na_tags(self, user: str = None):
        """
        This method fill NA tags
        @param user:
        @return:
        """
        tags = []
        keys = ['User', 'Owner', 'Manager', 'Project', 'Environment', 'Email']
        value = 'NA'
        for key in keys:
            if user and key == 'User':
                tags.append({'Key': key, 'Value': user})
            elif user and key == 'Email':
                tags.append({'Key': key, 'Value': f'{user}@redhat.com'})
            else:
                tags.append({'Key': key, 'Value': value})
        return tags

    def _get_username_from_cloudtrail(self, start_time: datetime, resource_id: str, resource_type: str):
        """
        This method return username fom cloudtrail
        @param start_time:
        @param resource_id:
        @param resource_type:
        @return:
        """
        return self.cloudtrail.get_username_by_instance_id_and_time(start_time=start_time, resource_id=resource_id, resource_type=resource_type)

    def _get_resource_data(self, resource_method: callable):
        """
        This method returns the resource_data
        @return:
        """
        resource_data = resource_method()
        if 'ec2_operations' not in str(resource_method):
            _, resource_list = self.ec2_operations.scan_cluster_or_non_cluster_instance(resource_data)
        else:
            _, resource_list = self.ec2_operations.scan_cluster_non_cluster_resources(resource_data)
        return resource_list

    def _convert_datetime_format(self, date_time: datetime):
        """
        This method convert datetime to YYYY/MM/DD H:M:S
        @param date_time:
        @return:
        """
        return date_time.strftime('%Y/%m/%d %H:%M:%S')

    def _build_tag(self, key: str, value: any):
        """
        This method return Key value pair
        @param key:
        @param value:
        @return:
        """
        if isinstance(value, datetime):
            value = self._convert_datetime_format(date_time=value)
        return {'Key': key, 'Value': value}

    def _get_tags_from_instance_item(self, instance_item: dict):
        tags = []
        username = ''
        if instance_item.get('Tags'):
            tags.extend(
                [tag for tag in instance_item.get('Tags') if not tag.get('Key') == 'Name'])
            for tag in instance_item.get('Tags'):
                if tag.get('Key') == 'User':
                    username = tag.get('Value')
                elif tag.get('Key') == 'LaunchTime':
                    tags.append({'Key': 'LaunchTime', 'Value': tag.get('Key')})
        if not username:
            tags.extend(self._append_input_tags())
            username = self._get_username_from_cloudtrail(start_time=instance_item.get('LaunchTime'),
                                                          resource_id=instance_item.get('InstanceId'),
                                                          resource_type='AWS::EC2::Instance')
            launch_time = instance_item.get('LaunchTime')
            tags.append(self._build_tag(key='LaunchTime', value=launch_time))
        return tags, username

    def _get_tags_fom_attachments(self, attachments: list):
        """
        This method return tags from attachments
        @param attachments:
        @return:
        """
        tags = []
        username = ''
        if attachments:
            for attachment in attachments:
                for item in self._get_instances_data(attachment.get('InstanceId')):
                    item_tags, username = self._get_tags_from_instance_item(instance_item=item)
        else:
            tags.extend(self._append_input_tags())
        return tags, username

    def _get_tags_from_snapshot_description_images(self, description: str):
        tags = []
        username = ''
        if description and 'Created' in description:
            image_id = description.split(" ")[-1]
            images = self.ec2_client.describe_images(Owners=['self'])['Images']
            for image in images:
                if image.get('ImageId') == image_id:
                    if image.get('tags'):
                        tags.extend(
                            [tag for tag in image.get('Tags') if not tag.get('Key') == "Name"])
                    else:
                        tags.extend(self._append_input_tags())
                    start_time = datetime.fromisoformat(image.get('CreationDate')[:-1] + '+00:00')
                    username = self._get_username_from_cloudtrail(start_time=start_time, resource_id=image_id, resource_type='AWS::EC2::Ami')
        return tags, username


