import datetime
import os
import uuid
from operator import le

import boto3
import pytest
from moto import mock_cloudtrail, mock_ec2, mock_dynamodb, mock_iam

from cloud_governance.policy.policy_operations.aws.dynamodb_upload_data.upload_data_to_dynamodb import UploadDataToDynamoDb
from cloud_governance.policy.aws.ec2_stop import EC2Stop
from cloud_governance.policy.policy_operations.aws.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['TABLE_NAME'] = 'test_table'
os.environ['dry_run'] = 'no'


@mock_ec2
@mock_cloudtrail
@mock_dynamodb
@pytest.mark.skip(reason="May be enabled in future")
def test_upload_data_ec2_stop():
    """
    This method upload data to cloudtrail, test ec2_stop
    @return:
    """
    boto3.setup_default_session()
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'}]
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][0].get('InstanceId')
    ec2_client.stop_instances(InstanceIds=[instance_id])
    dynamo_db = UploadDataToDynamoDb()
    dynamo_db.set_region(value='us-east-1')
    dynamo_db.set_table_name(value='test_table')
    event_id = str(uuid.uuid1())
    mock_log_data = [{
        'EventId': event_id,
        'EventTime': datetime.datetime.now(),
        'EventName': 'StopInstances',
        'AWS::EC2::Instance': instance_id,
        'Username': 'cloud-governance-user-test',
        'Resources': [{'ResourceType': 'AWS::EC2::Instance', 'ResourceName': instance_id}]
    }]
    dynamo_db._create_table_not_exists(primary_key='EventId')
    dynamo_db._upload_to_dynamo_db_table(data=mock_log_data)
    ec2_stop_obj = EC2Stop()
    ec2_stop_obj._EC2Stop__fetch_stop_instance(sign=le, instance_days=1, delete_instance_days=0)
    amis = ec2_client.describe_images(Owners=['self'])['Images']
    snapshot_id = amis[0].get('BlockDeviceMappings')[0].get('Ebs').get('SnapshotId')
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'], SnapshotIds=[snapshot_id])['Snapshots']
    assert len(snapshots) == len(amis)


@pytest.mark.skip(reason="May be enabled in future")
@mock_ec2
@mock_cloudtrail
@mock_dynamodb
@mock_iam
def test_upload_data_tag_non_cluster_resource():
    iam_client = boto3.client('iam')
    iam_client.create_user(UserName='cloud-governance-test', Tags=[{'Key': 'User', 'Value': 'cloud-governance-test'},
                                                                   {'Key': 'Project', 'Value': 'cloud-governance'},
                                                                   {'Key': 'Environment', 'Value': 'Test'}])
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    mandatory_tags = {'test': 'ec2-update'}
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)['Instances'][0].get('InstanceId')
    tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no', region=os.environ.get('AWS_DEFAULT_REGION'))
    event_id = str(uuid.uuid1())
    mock_log_data = [{
        'EventId': event_id,
        'EventTime': datetime.datetime.now(),
        'EventName': 'RunInstances',
        'AWS::EC2::Instance': instance_id,
        'Username': 'cloud-governance-test',
        'Resources': [{'ResourceType': 'AWS::EC2::Instance', 'ResourceName': instance_id}]
    }]
    dynamo_db = UploadDataToDynamoDb()
    dynamo_db.set_region(value='us-east-1')
    dynamo_db.set_table_name(value='test_table')
    dynamo_db._create_table_not_exists(primary_key='EventId')
    dynamo_db._upload_to_dynamo_db_table(data=mock_log_data)
    assert len(tag_resources.non_cluster_update_ec2()) == 1


@mock_dynamodb
def test_upload_data():
    """
    This method test data is uploaded to table correctly or not
    @return:
    """
    dynamo_db = UploadDataToDynamoDb()
    dynamo_db.set_region(value='us-east-1')
    dynamo_db.set_table_name(value='test_table')
    dynamo_db._create_table_not_exists(primary_key='Id')
    mock_log_data = [{
        'Id': '1',
        'EventTime': datetime.datetime.now(),
        'Username': 'cloud-governance-user-test'
    }]
    assert 1 == dynamo_db._upload_to_dynamo_db_table(data=mock_log_data)






