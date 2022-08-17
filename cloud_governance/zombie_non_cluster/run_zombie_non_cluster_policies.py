import os
import datetime
from ast import literal_eval

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.s3.s3_operations import S3Operations
from cloud_governance.common.mails.mail import Mail
from cloud_governance.policy.zombie_cluster_resource import ZombieClusterResources


class NonClusterZombiePolicy:

    def __init__(self):
        self._account = os.environ.get('account', '')
        self._dry_run = os.environ.get('dry_run', 'yes')
        self._region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._policy = os.environ.get('policy', '')
        self._policy_output = os.environ.get('policy_output', '')
        self._ec2_client = boto3.client('ec2', region_name=self._region)
        self._ec2_operations = EC2Operations(region=self._region)
        self._s3_client = boto3.client('s3')
        self._iam_operations = IAMOperations()
        self._iam_client = boto3.client('iam')
        self._cluster_prefix = 'kubernetes.io/cluster'
        self._zombie_cluster = ZombieClusterResources(cluster_prefix=self._cluster_prefix)
        self._s3operations = S3Operations(region_name=self._region)
        self._cloudtrail = CloudTrailOperations(region_name=self._region)
        self._special_user_mails = os.environ.get('special_user_mails', '{}')
        self._mail = Mail()

    def _literal_eval(self):
        tags = {}
        if self._special_user_mails:
            tags = literal_eval(self._special_user_mails)
        return tags

    def _check_live_cluster_tag(self, tags: list, active_clusters: list):
        """
        This method returns True if it is live cluster tag is active False not
        @param tags:
        @return:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').startswith(self._cluster_prefix):
                    return tag.get('Key') in active_clusters
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
            return 'NA'
        return 'NA'

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
                resource_str += resource_data[-1]
                upload_data.append(resource_str)
            else:
                upload_data.append(resource_data)
        return upload_data

    def _get_resource_username(self, create_date: datetime, resource_id: str, resource_type: str):
        """
        Get Username from the cloudtrail
        @param create_date:
        @param resource_id:
        @param resource_type:
        @return:
        """
        return self._cloudtrail.get_username_by_instance_id_and_time(start_time=create_date, resource_id=resource_id, resource_type=resource_type)

    def _get_policy_value(self, tags: list):
        """
        This method beautify the value
        @param tags:
        @return:
        """
        policy_value = self._get_tag_name_from_tags(tags=tags, tag_name='Policy').strip()
        return policy_value.replace('_', '').replace('-', '').upper()

