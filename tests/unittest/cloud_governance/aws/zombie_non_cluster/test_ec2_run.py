import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.aws.ec2_run import EC2Run

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@mock_ec2
def test_ec2_run():
    """
    This method test in-use ebs volumes
    @return:
    """
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    ec2_client = boto3.client('ec2', region_name=region)
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)
    ec2_run = EC2Run()
    assert 1 == len(ec2_run.run())
