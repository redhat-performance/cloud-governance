import os
from operator import le

import boto3
from moto import mock_ec2

from cloud_governance.policy.ec2_stop import EC2Stop

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_ec2_stop():
    """
    This method tests, termination of stopped instance more than 30 days and create an image, snapshot
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'}]
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][0].get('InstanceId')
    ec2_client.stop_instances(InstanceIds=[instance_id])
    ec2_stop = EC2Stop()
    ec2_stop._EC2Stop__fetch_stop_instance(sign=le, instance_age=1)
    amis = ec2_client.describe_images(Owners=['self'])['Images']
    snapshot_id = amis[0].get('BlockDeviceMappings')[0].get('Ebs').get('SnapshotId')
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'], SnapshotIds=[snapshot_id])['Snapshots']
    assert len(snapshots) == len(amis)


@mock_ec2
def test_ec2_stop_not_delete():
    """
        This method tests,not termination of stopped instance more than 30 days and create an image, snapshot using Policy=NOT_DELETE
        @return:
        """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'}, {'Key': 'policy', 'Value': 'not_delete'}]
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][
        0].get('InstanceId')
    ec2_client.stop_instances(InstanceIds=[instance_id])
    ec2_stop = EC2Stop()
    ec2_stop._EC2Stop__fetch_stop_instance(sign=le, instance_age=1)
    instances = ec2_client.describe_instances()['Reservations']
    assert len(instances) == 1
