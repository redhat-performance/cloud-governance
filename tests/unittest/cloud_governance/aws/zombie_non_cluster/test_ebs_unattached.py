import os

import boto3
from moto import mock_ec2

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from cloud_governance.policy.aws.ebs_unattached import EbsUnattached

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_ebs_unattached_deleted():
    """
    This method test the ebs volume is deleted
    @return:
    """
    os.environ['policy'] = 'ebs_unattached'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    ec2_client.create_volume(AvailabilityZone='us-east-2a', Size=10)
    zombie_elastic_ips = NonClusterZombiePolicy()
    zombie_elastic_ips.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    zombie_elastic_ips._check_resource_and_delete(resource_name='Ebs Volume',
                                                  resource_id='VolumeId',
                                                  resource_type='CreateVolume',
                                                  resource=ec2_client.describe_volumes()['Volumes'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    assert 0 == len(ec2_client.describe_volumes()['Volumes'])


@mock_ec2
def test_ebs_unattached_skip_deletion():
    """
    This method skip the ebs unattached deletion
    @return:
    """
    os.environ['policy'] = 'ebs_unattached'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    tags = [{'Key': 'policy', 'Value': 'skip'}]
    ec2_client.create_volume(AvailabilityZone='us-east-2a', Size=10, TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags}])
    zombie_elastic_ips = NonClusterZombiePolicy()
    zombie_elastic_ips.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    zombie_elastic_ips._check_resource_and_delete(resource_name='Ebs Volume',
                                                  resource_id='VolumeId',
                                                  resource_type='CreateVolume',
                                                  resource=ec2_client.describe_volumes()['Volumes'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    assert 1 == len(ec2_client.describe_volumes()['Volumes'])
