from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.utils import Utils


class TagClusterOperations:
    """
    This class tags AWS resources
    """

    def __init__(self, region: str, input_tags: dict = None,  cluster_name: str = None,  cluster_prefix: str = None, dry_run: str = None, cluster_only: bool = None):
        self.cluster_only = cluster_only
        self.cluster_prefix = cluster_prefix
        self.utils = Utils(region=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.ec2_operations = EC2Operations(region=region)
        self.iam_operations = IAMOperations()
        self.cluster_name = cluster_name
        self.input_tags = input_tags
        self.cloudtrail = CloudTrailOperations(region_name='us-east-1')
        self._get_username_from_instance_id_and_time = CloudTrailOperations(region_name=region).get_username_by_instance_id_and_time
        self.dry_run = dry_run
        self.iam_users = self.iam_operations.get_iam_users_list()

    def _input_tags_list_builder(self):
        """
        This method build tags list according to input tags dictionary
        @return:
        """
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def _get_instances_data(self):
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

    def _fill_na_tags(self, user: str = None):
        """
        This method fill the NA tags
        @param user:
        @return:
        """
        keys = ['User', 'Owner', 'Manager', 'Project', 'Environment', 'Email']
        tags = []
        value = 'NA'
        for key in keys:
            if user and user == 'User':
                value = user
            elif user and user == 'Email':
                value = f'{user}@redhat.com'
            else:
                tags.append({'Key': key, 'Value': value})
        return tags

    def get_user_name_from_name_tag(self, tags: list):
        """
        This method retuns the username from the name tag verified  with iam users
        :param tags:
        :return:
        """
        user_name = self.ec2_operations.get_tag_value_from_tags(tags=tags, tag_name='User')
        if user_name in self.iam_users:
            return user_name
        else:
            name_tag = self.ec2_operations.get_tag_value_from_tags(tags=tags, tag_name='Name')
            for user in self.iam_users:
                if user in name_tag:
                    return user
            return None

    def get_username(self, start_time: datetime, resource_id: str, resource_type: str, tags: list):
        """
        This method returns the username
        :return:
        """
        iam_username = self.get_user_name_from_name_tag(tags=tags)
        if not iam_username:
            return self._get_username_from_instance_id_and_time(start_time=start_time, resource_id=resource_id, resource_type=resource_type)
        return iam_username
