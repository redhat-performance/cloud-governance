import datetime

import boto3
from moto import mock_ec2, mock_cloudwatch

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.unused_nat_gateway import UnUsedNatGateway
from tests.unittest.configs import AWS_DEFAULT_REGION, NAT_GATEWAY_NAMESPACE


@mock_ec2
def test_unused_nat_gateway_dry_run_yes():
    """
    This method tests the unused_nat_gateway collected by dry_run=yes
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id)
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0


@mock_cloudwatch
@mock_ec2
def test_unused_nat_gateway_dry_run_yes_collect_none():
    """
    This method tests the unused_nat_gateway not collected by dry_run=yes
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    cloud_watch_client = boto3.client('cloudwatch', region_name=AWS_DEFAULT_REGION)
    subnet = ec2_client.describe_subnets()['Subnets'][0]
    route_table = ec2_client.create_route_table(VpcId=subnet.get('VpcId')).get('RouteTable', {})
    nat_gateway = ec2_client.create_nat_gateway(SubnetId=subnet.get('SubnetId')).get('NatGateway', {})
    ec2_client.create_route(NatGatewayId=nat_gateway.get('NatGatewayId'), RouteTableId=route_table.get('RouteTableId'))
    cloud_watch_client.put_metric_data(Namespace=NAT_GATEWAY_NAMESPACE, MetricData=[
        {
            'MetricName': 'ActiveConnectionCount',
            'Dimensions': [
                {
                    'Name': 'NatGatewayId',
                    'Value': nat_gateway.get('NatGatewayId')
                },
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': 123.0,
            'Values': [123.0],
            'Unit': 'Count',
        }
    ])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 0


@mock_ec2
def test_unused_nat_gateway_dry_run_no():
    """
    This method verifies the data is collecting by dry_run = no
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    ec2_client.create_nat_gateway(SubnetId=subnet_id)
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    response = response[0]
    assert response.get('CleanUpDays') == 1


@mock_ec2
def test_unused_nat_gateway___dry_run_no_7_days_action_delete():
    """
    This method tests the deletion of unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    tags = [{'Key': 'DaysCount', 'Value': f'{datetime.datetime.utcnow().date()}@7'}]
    ec2_client.create_nat_gateway(SubnetId=subnet_id, TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    response = response[0]
    assert response.get('CleanUpDays') == 7
    assert response.get('ResourceAction') == 'True'


@mock_ec2
def test_unused_nat_gateway___dry_run_no_skips_delete():
    """
    This method tests skip deletion of unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    tags = [{'Key': 'DaysCount', 'Value': f'{datetime.datetime.utcnow().date()}@7'},
            {'Key': 'policy', 'Value': 'not-delete'}]
    ec2_client.create_nat_gateway(SubnetId=subnet_id, TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    response = response[0]
    assert response.get('CleanUpDays') == 7
    assert response.get('ResourceAction') == 'False'


@mock_ec2
def test_unused_nat_gateway___dry_run_no_skips_active_cluster_resource():
    """
    This method tests the skip collection of unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    subnet_id = ec2_client.describe_subnets()['Subnets'][0].get('SubnetId')
    tags = [{'Key': 'kubernetes.io/cluster/test', 'Value': 'owned'}]
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1,
                             MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    ec2_client.create_nat_gateway(SubnetId=subnet_id, TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 0
