import os

import boto3
from moto import mock_ec2

from cloud_governance.aws.tag_non_cluster.update_na_tag_resources import UpdateNATags
os.environ['SLEEP_SECONDS'] = '0'


@mock_ec2
def test_create_csv():
    """
    This method test csv is generated or not
    @return:
    """
    tags = [
        {"Key": 'User', 'Value': 'NA'}
    ]
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name='us-east-2')
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1,TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
    update_na_tags = UpdateNATags(region='us-east-2', file_name='tag_na.csv')
    update_na_tags.create_csv()
    assert os.path.exists('tag_na.csv')
    if os.path.exists('tag_na.csv'):
        os.remove('tag_na.csv')


@mock_ec2
def test_update_tags():
    """
    This method tests update of tags to resource
    @return:
    """
    tags = [
        {"Key": 'User', 'Value': 'NA'}
    ]
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name='us-east-2')
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1, TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
    update_na_tags = UpdateNATags(region='us-east-2', file_name='tag_na.csv')
    update_na_tags.create_csv()
    update_na_tags = UpdateNATags(region='us-east-2', file_name='tag_na.csv')
    assert update_na_tags.update_tags() == 1
    if os.path.exists('tag_na.csv'):
        os.remove('tag_na.csv')
