from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class TagClusterOperations:
    """
    This class tags AWS resources
    """

    CLUSTER_ID_COST_ALLOCATION_TAG = 'cluster_id'

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
        self._regional_cloudtrail = CloudTrailOperations(region_name=region)
        self._get_username_from_instance_id_and_time = self._regional_cloudtrail.get_username_by_instance_id_and_time
        self.dry_run = dry_run
        self.iam_users = self.iam_operations.get_iam_users_list()
        self._automation_user = self._get_automation_username()

    @staticmethod
    def _get_automation_username():
        """
        Identify the current caller (the automation/service account running
        this policy) so it can be excluded from CloudTrail fallback searches.
        """
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            arn = identity.get('Arn', '')
            return arn.split('/')[-1] if '/' in arn else ''
        except Exception:
            return ''

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

    def get_username(self, start_time: datetime, resource_id: str, resource_type: str,
                     tags: list, cluster_id: str = ''):
        """
        This method returns the username using multiple strategies:
        1. Check existing tags (User tag, Name tag)
        2. CloudTrail - resource creation event (RunInstances, etc.)
        3. CloudTrail - any event on this resource by a known IAM user
           (handles managed services like ROSA where service accounts create
           resources but user events like CreateTags may exist)
        4. CloudTrail - trace cluster IAM roles to find who created them
           (handles ROSA/OSD where instances are created by service accounts
           but IAM roles are created by the user)
        :return:
        """
        exclude = {self._automation_user} if self._automation_user else set()
        iam_username = self.get_user_name_from_name_tag(tags=tags)
        if not iam_username:
            ct_username = self._get_username_from_instance_id_and_time(
                start_time=start_time, resource_id=resource_id,
                resource_type=resource_type)
            if ct_username and (ct_username in self.iam_users or ct_username == 'AutoScaling'):
                return ct_username
            if cluster_id:
                iam_username = self.cloudtrail.get_username_from_cluster_role(
                    cluster_id=cluster_id, iam_users=self.iam_users,
                    launch_time=start_time)
                if iam_username:
                    logger.info(f'Resolved cluster owner {iam_username} via IAM '
                                f'role lookup for cluster {cluster_id}')
                    return iam_username
            iam_username = self._regional_cloudtrail.get_username_from_resource_events(
                resource_id=resource_id, iam_users=self.iam_users,
                start_time=start_time, exclude_users=exclude)
        return iam_username

    def get_username_from_cluster_instances(self, resources: list, cluster_name: str):
        """
        Search all instances in a cluster for a valid User tag.
        If any instance already has a tagged owner, return that username.
        Handles managed services (ROSA, EKS) where CloudTrail cannot attribute
        the creator - if at least one instance was tagged, propagate to siblings.
        @param resources: list of instance groups from the cluster
        @param cluster_name: the cluster identifier to match
        @return: username string or None
        """
        for instance_group in resources:
            for item in instance_group:
                tags = item.get('Tags', [])
                for tag in tags:
                    if any(prefix in tag.get('Key', '') for prefix in self.cluster_prefix):
                        if cluster_name in tag.get('Key', ''):
                            user = self.ec2_operations.get_tag_value_from_tags(
                                tags=tags, tag_name='User')
                            if user and user != 'NA' and user in self.iam_users:
                                return user
        return None
