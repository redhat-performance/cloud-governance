import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.zombie_snapshots import ZombieSnapshots


os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_zombie_snapshots():
    """
    This method tests delete of the ami related snapshots
    @return:
    """
    region = os.environ.get('AWS_DEFAULT_REGION')
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieSnapshot'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'}
    ]
    ec2_client = boto3.client('ec2', region_name=region)
    default_ami_id = 'ami-03cf127a'
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)['Instances'][0]['InstanceId']
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))
    imageid = ec2_client.create_image(InstanceId=instance_id,
                                      Name='Cloud-Governance-TestImage',
                                      TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = ec2_client.describe_images(ImageIds=[imageid])['Images'][0].get('BlockDeviceMappings')[0].get('Ebs').get('SnapshotId')
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=imageid)
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    zombie_snapshot = ZombieSnapshots()
    zombie_snapshot.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 0


@mock_ec2
def test_zombie_snapshots_not_delete():
    """
    This method tests not delete of the ami related snapshots by policy=NOT_DELETE
    @return:
    """
    region = os.environ.get('AWS_DEFAULT_REGION')
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieSnapshot'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'notdelete'}
    ]
    ec2_client = boto3.client('ec2', region_name=region)
    default_ami_id = 'ami-03cf127a'
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)['Instances'][0]['InstanceId']
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))
    imageid = ec2_client.create_image(InstanceId=instance_id,
                                      Name='Cloud-Governance-TestImage',
                                      TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = ec2_client.describe_images(ImageIds=[imageid])['Images'][0].get('BlockDeviceMappings')[0].get('Ebs').get('SnapshotId')
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=imageid)
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    zombie_snapshot = ZombieSnapshots()
    zombie_snapshot.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 1
