import os

import boto3
from moto import mock_ec2, mock_cloudwatch

from cloud_governance.policy.aws.ec2_idle import EC2Idle

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'yes'


@mock_cloudwatch
@mock_ec2
def test_ec2_idle_cluster():
    """
    This method test to skip cluster
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'kubernetes.io/cluster/cloudgovernanceunittest', 'Value': 'owned'}, {'Key': 'User', 'Value': 'cloud-governance'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    ec2_idle = EC2Idle()
    actual_result = ec2_idle._EC2Idle__stop_idle_instances(instance_launch_days=-1)
    assert 0 == len(actual_result)


@mock_cloudwatch
@mock_ec2
def test_ec2_idle():
    """
    This method check the instance is deleted or not
    @return:
    """
    expected_result = 'stopped'
    os.environ['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])

    ec2_idle = EC2Idle()
    ec2_idle._EC2Idle__stop_idle_instances(instance_launch_days=-1)
    actual_result = ec2_client.describe_instances()['Reservations'][0]['Instances'][0].get('State').get('Name')
    assert expected_result == actual_result


@mock_cloudwatch
@mock_ec2
def test_ec2_idle_not_delete():
    """
    This method checks the instance is no_delete if policy=notdelete
    @return:
    """
    expected_result = 1
    os.environ['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': 'policy', 'Value': 'notdelete'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])

    ec2_idle = EC2Idle()
    actual_result = ec2_idle._EC2Idle__stop_idle_instances(instance_launch_days=-1)
    assert expected_result == len(actual_result)

