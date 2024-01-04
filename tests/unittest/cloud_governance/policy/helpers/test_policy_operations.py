import datetime

import boto3
from moto import mock_ec2, mock_s3, mock_iam

from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations
from cloud_governance.main.environment_variables import environment_variables


@mock_ec2
@mock_s3
@mock_iam
def test_verify_and_delete_resource_not_stopped():
    """
    This method tests verify_and_delete_resource
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    resource_id = resource[0].get('InstanceId')
    aws_cleanup_operations = AWSPolicyOperations()
    clean_up_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert not aws_cleanup_operations.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                             clean_up_days=clean_up_days)
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1


@mock_ec2
@mock_s3
@mock_iam
def test_verify_and_delete_resource_stopped():
    """
    This method tests verify_and_delete_resource
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.datetime.now() - datetime.timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    resource_id = resource[0].get('InstanceId')
    aws_cleanup_operations = AWSPolicyOperations()
    clean_up_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert aws_cleanup_operations.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                             clean_up_days=clean_up_days)
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_verify_and_delete_resource_skip():
    """
    This method tests verify_and_delete_resource
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.datetime.now() - datetime.timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"},
            {'Key': "Skip", "Value": f"notdelete"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    resource_id = resource[0].get('InstanceId')
    aws_cleanup_operations = AWSPolicyOperations()
    clean_up_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert not aws_cleanup_operations.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                             clean_up_days=clean_up_days)
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1
