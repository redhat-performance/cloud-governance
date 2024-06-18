
import boto3
from moto import mock_ec2, mock_s3

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.ebs_in_use import EbsInUse
from tests.unittest.configs import AWS_DEFAULT_REGION


@mock_ec2
def test_ebs_in_use():
    """
    This method test in-use ebs volumes
    @return:
    """
    environment_variables.environment_variables_dict['policy'] = 'ebs_in_use'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    volume_id = ec2_client.create_volume(Size=10, AvailabilityZone='us-east-1a')['VolumeId']
    default_ami_id = 'ami-03cf127a'
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)['Instances'][0]['InstanceId']
    ec2_client.attach_volume(InstanceId=instance_id, VolumeId=volume_id, Device='/dev/sda1')
    ebs_in_use = EbsInUse()
    ebs_in_use.set_policy('ebs_in_use')
    assert 2 == len(ebs_in_use.run())


@mock_s3
@mock_ec2
def test_ebs_in_use_s3_upload():
    """
    This method test the data is upload t s3 or not
    @return:
    """
    environment_variables.environment_variables_dict['policy'] = 'ebs_in_use'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='test-upload-data', CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
    policy_output = 's3://test-upload-data/test'
    s3operations = S3Operations(region_name='us-east-1')
    ebs_in_use = EbsInUse()
    assert s3operations.save_results_to_s3(policy='ebs_in_use', policy_output=policy_output, policy_result=ebs_in_use.run()) is None
