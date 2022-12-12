import os

import boto3
from moto import mock_ec2

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy
from cloud_governance.policy.aws.nat_gateway_unused import NatGatewayUnused

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
def test_nat_gateway_unused():
    """
    This method tests, deletion od unused of NatGateways
    @return:
    """
    os.environ['policy'] = 'nat_gateway_unused'
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id)
    nat_gateway_unused = NonClusterZombiePolicy()
    nat_gateway_unused.set_dryrun(value='no')
    nat_gateway_unused.set_policy(value='nat_gateway_unused')
    nat_gateway_unused.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    nat_gateway_unused._check_resource_and_delete(resource_name='Nat Gateway',
                                                  resource_id='NatGatewayId',
                                                  resource_type='CreateNatGateway',
                                                  resource=ec2_client.describe_nat_gateways()['NatGateways'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    nat_gateways = ec2_client.describe_nat_gateways()['NatGateways']
    assert len(nat_gateways) == 1 and nat_gateways[0].get('State') == 'deleted'


@mock_ec2
def test_nat_gateway_unused_not_delete():
    """
    This method tests, deletion od unused of NatGateways
    @return:
    """
    os.environ['policy'] = 'nat_gateway_unused'
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestZombieNatGateway'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'not-delete'}
    ]
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id, TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}])
    nat_gateway_unused = NonClusterZombiePolicy()
    nat_gateway_unused.set_dryrun(value='no')
    nat_gateway_unused.set_policy(value='nat_gateway_unused')
    nat_gateway_unused.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    nat_gateway_unused._check_resource_and_delete(resource_name='Nat Gateway',
                                                  resource_id='NatGatewayId',
                                                  resource_type='CreateNatGateway',
                                                  resource=ec2_client.describe_nat_gateways()['NatGateways'][0],
                                                  empty_days=0,
                                                  days_to_delete_resource=0)
    nat_gateways = ec2_client.describe_nat_gateways()['NatGateways']
    assert len(nat_gateways) == 1 and nat_gateways[0].get('State') == 'available'
