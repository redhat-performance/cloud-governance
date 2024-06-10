from datetime import datetime
from unittest.mock import patch

import boto3
from moto import mock_ec2

from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.zombie_snapshots import ZombieSnapshots
from tests.unittest.configs import DRY_RUN_YES, AWS_DEFAULT_REGION, INSTANCE_TYPE_T2_MICRO, DEFAULT_AMI_ID, \
    TEST_USER_NAME, DRY_RUN_NO



@mock_ec2
def test_zombie_snapshots():
    """
    This method tests lists of the ami related snapshots
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'zombie_snapshots'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}]
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)

    # delete default snapshots and images
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))

    # create infra
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME,
                                       TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = (ec2_client.describe_images(ImageIds=[image_id])['Images'][0].get('BlockDeviceMappings')[0]
                   .get('Ebs').get('SnapshotId'))
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=image_id)
    ec2_client.terminate_instances(InstanceIds=[instance_id])

    # run zombie_snapshots
    zombie_snapshots = ZombieSnapshots()
    response = zombie_snapshots.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
    assert get_tag_value_from_tags(tags=ec2_client.describe_snapshots(OwnerIds=['self'],
                                                                      SnapshotIds=[snapshot_id])['Snapshots'][0]['Tags'],
                                   tag_name='DaysCount')


@mock_ec2
def test_zombie_snapshots_delete():
    """
    This method tests delete of the ami related snapshots
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'zombie_snapshots'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME},
            {'Key': 'DaysCount', 'Value': f'{datetime.utcnow().date()}@7'}]
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)

    # delete default snapshots and images
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))

    # create infra
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME,
                                       TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = (ec2_client.describe_images(ImageIds=[image_id])['Images'][0].get('BlockDeviceMappings')[0]
                   .get('Ebs').get('SnapshotId'))
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=image_id)
    ec2_client.terminate_instances(InstanceIds=[instance_id])

    # run zombie_snapshots
    zombie_snapshots = ZombieSnapshots()
    response = zombie_snapshots.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 0
    assert len(response) == 1


@mock_ec2
def test_zombie_snapshots_skip():
    """
    This method tests skip delete of the ami related snapshots
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'zombie_snapshots'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'policy', 'Value': 'not-delete'},
            {'Key': 'DaysCount', 'Value': f'{datetime.utcnow().date()}@7'}]
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)

    # delete default snapshots and images
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))

    # create infra
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME,
                                       TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = (ec2_client.describe_images(ImageIds=[image_id])['Images'][0].get('BlockDeviceMappings')[0]
                   .get('Ebs').get('SnapshotId'))
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=image_id)
    ec2_client.terminate_instances(InstanceIds=[instance_id])

    # run zombie_snapshots
    zombie_snapshots = ZombieSnapshots()
    response = zombie_snapshots.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 1
    assert len(response) == 1


@mock_ec2
def test_zombie_snapshots_contains_cluster_tag():
    """
    This method tests snapshot having the live cluster
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'zombie_snapshots'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'policy', 'Value': 'not-delete'},
            {'Key': 'DaysCount', 'Value': f'{datetime.utcnow().date()}@7'},
            {'Key': 'kubernetes.io/cluster/test-zombie-cluster', 'Value': f'owned'}]
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)

    # delete default snapshots and images
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
    images = ec2_client.describe_images()['Images']
    for image in images:
        ec2_client.deregister_image(ImageId=image.get('ImageId'))
    for snapshot in snapshots:
        ec2_client.delete_snapshot(SnapshotId=snapshot.get('SnapshotId'))

    # create infra
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME,
                                       TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}]).get('ImageId')
    snapshot_id = (ec2_client.describe_images(ImageIds=[image_id])['Images'][0].get('BlockDeviceMappings')[0]
                   .get('Ebs').get('SnapshotId'))
    ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
    ec2_client.deregister_image(ImageId=image_id)

    # run zombie_snapshots
    zombie_snapshots = ZombieSnapshots()
    response = zombie_snapshots.run()
    assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 1
    assert len(response) == 0


def test_zombie_snapshots_no_zombies():
    """
    This method tests snapshot having the active AMI
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'zombie_snapshots'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'policy', 'Value': 'not-delete'},
            {'Key': 'DaysCount', 'Value': f'{datetime.utcnow().date()}@7'}]
    snapshot_id = 'mock_snapshot_id'
    image_id = 'mock_image_id'

    def mock_create_image(*args, **kwargs):
        mock_response = {
            'Images': [
                {
                    'ImageId': image_id
                }
            ]
        }
        return mock_response

    def mock_create_snapshot(*args, **kwargs):
        return {
            'Snapshots': [
                {'SnapshotId': snapshot_id}
            ]
        }

    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_images.return_value = mock_create_image()
        mock_client.return_value.describe_snapshots.return_value = mock_create_snapshot()

        # run zombie_snapshots
        zombie_snapshots = ZombieSnapshots()
        response = zombie_snapshots.run()
        ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
        assert len(ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']) == 1
        assert len(response) == 0
