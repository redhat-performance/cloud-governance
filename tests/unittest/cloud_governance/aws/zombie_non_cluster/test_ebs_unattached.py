import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from cloud_governance.policy.aws.ebs_unattached import EbsUnattached

AWS_DEFAULT_REGION = 'us-east-2'


@mock_ec2
def test_ebs_unattached_deleted():
    """
    This method test the ebs volume is deleted
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.create_volume(AvailabilityZone='us-east-2a', Size=10)
    ebs_unattached = NonClusterZombiePolicy()
    ebs_unattached.set_dryrun(value='no')
    ebs_unattached.set_policy(value='ebs_unattached')
    ebs_unattached.set_region(value=AWS_DEFAULT_REGION)
    ebs_unattached.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    ebs_unattached._check_resource_and_delete(resource_name='Ebs Volume',
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
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [{'Key': 'policy', 'Value': 'skip'}]
    ec2_client.create_volume(AvailabilityZone='us-east-2a', Size=10,
                             TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags}])
    ebs_unattached = NonClusterZombiePolicy()
    ebs_unattached.set_dryrun(value='no')
    ebs_unattached.set_policy(value='ebs_unattached')
    ebs_unattached.set_region(value=AWS_DEFAULT_REGION)
    ebs_unattached.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    ebs_unattached._check_resource_and_delete(resource_name='Ebs Volume',
                                              resource_id='VolumeId',
                                              resource_type='CreateVolume',
                                              resource=ec2_client.describe_volumes()['Volumes'][0],
                                              empty_days=0,
                                              days_to_delete_resource=0)
    assert 1 == len(ec2_client.describe_volumes()['Volumes'])


@mock_ec2
def test_skip_live_cluster_volumes():
    """
    This method skips the live cluster volumes
    @return:
    """
    os.environ['policy'] = 'ebs_unattached'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'},
            {'Key': 'kubernetes.io/cluster/test', 'Value': 'owned'}]
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    ec2_client.create_volume(AvailabilityZone='us-east-2a', Size=10,
                             TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags}])
    ebs_unattached = EbsUnattached()
    ebs_unattached.run()
    assert 2 == len(ec2_client.describe_volumes()['Volumes'])
