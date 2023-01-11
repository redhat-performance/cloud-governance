
# Test dry run against ec2/ami name '@@@@####@@@@'
import os

import boto3
from moto import mock_ec2, mock_iam, mock_cloudtrail

from cloud_governance.policy.policy_operations.aws.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources

mandatory_tags = {'test': 'ec2-update'}
region_name = 'us-east-2'
tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no')
os.environ['SLEEP_SECONDS'] = '0'


@mock_cloudtrail
@mock_iam
@mock_ec2
def test_non_cluster_update_ec2():
    """
    This method tests the update tags to EC@ instance
    @return:
    """
    tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no')
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)
    assert len(tag_resources.non_cluster_update_ec2()) == 3


@mock_cloudtrail
@mock_iam
@mock_ec2
def test_update_ami():
    """
    This method tests the update tags of AMI image
    :return:
    """
    tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no')
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    ec2_client.create_image(InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    assert len(tag_resources.update_ami()) == 1


@mock_cloudtrail
@mock_iam
@mock_ec2
def test_update_volumes():
    """
    This method tests the Update the tags  of Volume
    :return:
    """
    tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no')
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.create_volume(AvailabilityZone=region_name, Size=123)
    ec2_client.create_volume(AvailabilityZone=region_name, Size=123)
    assert len(tag_resources.update_volumes()) == 2


@mock_cloudtrail
@mock_iam
@mock_ec2
def test_update_snapshots():
    """
    This method tests updates the tags of Snapshots
    :return:
    """
    tag_resources = TagNonClusterResources(input_tags=mandatory_tags, dry_run='no')
    ec2_client = boto3.client('ec2', region_name=region_name)
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))
    volume = ec2_client.create_volume(AvailabilityZone=region_name, Size=123)
    ec2_client.create_snapshot(VolumeId=volume['VolumeId'])
    assert len(tag_resources.update_snapshots()) == 1
