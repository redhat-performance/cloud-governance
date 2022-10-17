import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.aws.ebs_in_use import EbsInUse

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@mock_ec2
def test_ebs_in_use():
    """
    This method test in-use ebs volumes
    @return:
    """
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    ec2_client = boto3.client('ec2', region_name=region)
    volume_id = ec2_client.create_volume(Size=10, AvailabilityZone='us-east-1a')['VolumeId']
    default_ami_id = 'ami-03cf127a'
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)['Instances'][0]['InstanceId']
    ec2_client.attach_volume(InstanceId=instance_id, VolumeId=volume_id, Device='/dev/sda1')
    ebs_in_use = EbsInUse()
    assert 2 == len(ebs_in_use.run())
