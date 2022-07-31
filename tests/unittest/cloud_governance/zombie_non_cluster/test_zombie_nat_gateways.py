import os

import boto3
from moto import mock_ec2

from cloud_governance.policy.zombie_nat_gateways import ZombieNatGateways

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_zombie_nat_gateways():
    """
    This method tests, deletion od unsed of snapshots
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id)
    zombie_nat_gateways = ZombieNatGateways()
    zombie_nat_gateways.run()
    nat_gateways = ec2_client.describe_nat_gateways()['NatGateways']
    assert len(nat_gateways) == 1 and nat_gateways[0].get('State') == 'deleted'


@mock_ec2
def test_zombie_nat_gateways_not_delete():
    """
    This method tests, deletion od unsed of snapshots
    @return:
    """
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieNatGateway'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'not-delete'}
    ]
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id, TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}])
    zombie_nat_gateways = ZombieNatGateways()
    zombie_nat_gateways.run()
    nat_gateways = ec2_client.describe_nat_gateways()['NatGateways']
    assert len(nat_gateways) == 1 and nat_gateways[0].get('State') == 'available'
