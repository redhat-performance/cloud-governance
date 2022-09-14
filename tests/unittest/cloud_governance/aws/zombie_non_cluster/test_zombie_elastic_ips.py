import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.aws.zombie_elastic_ips import ZombieElasticIps

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_zombie_elastic_ips():
    """
    This method tests delete of zombie elastic ips
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    ec2_client.allocate_address(Domain='vpc')
    zombie_elastic_ips = ZombieElasticIps()
    zombie_elastic_ips.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 0


@mock_ec2
def test_zombie_elastic_ips_not_delete():
    """
    This method tests not delete of zombie elastic ips,if policy=NOT_DELETE
    @return:
    """
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieElasticIp'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'not-delete'}
    ]
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    zombie_elastic_ips = ZombieElasticIps()
    zombie_elastic_ips.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1

