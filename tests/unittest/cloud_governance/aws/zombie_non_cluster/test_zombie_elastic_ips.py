import os

import boto3
from moto import mock_ec2

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_zombie_elastic_ips():
    """
    This method tests delete of zombie elastic ips
    @return:
    """
    os.environ['policy'] = 'zombie_elastic_ips'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    ec2_client.allocate_address(Domain='vpc')
    zombie_elastic_ips = NonClusterZombiePolicy()
    zombie_elastic_ips.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    zombie_elastic_ips._check_resource_and_delete(resource_name='ElasticIp',
                                                  resource_id='AllocationId',
                                                  resource_type='AllocateAddress',
                                                  resource=ec2_client.describe_addresses()['Addresses'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 0


@mock_ec2
def test_zombie_elastic_ips_not_delete():
    """
    This method tests not delete of zombie elastic ips,if policy=NOT_DELETE
    @return:
    """
    os.environ['policy'] = 'zombie_elastic_ips'
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieElasticIp'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'skip'}
    ]
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    zombie_elastic_ips = NonClusterZombiePolicy()
    zombie_elastic_ips.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    zombie_elastic_ips._check_resource_and_delete(resource_name='ElasticIp',
                                                  resource_id='AllocationId',
                                                  resource_type='AllocateAddress',
                                                  resource=ec2_client.describe_addresses()['Addresses'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
