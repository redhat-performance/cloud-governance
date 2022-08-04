import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils


class TagClusterOperations:

    def __init__(self, input_tags: dict,  cluster_name: str,  cluster_prefix: str, region: str, dry_run: str, cluster_only: bool):
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
