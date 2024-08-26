import boto3
from moto import mock_ec2

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.ip_unattached import IpUnattached
from tests.unittest.configs import AWS_DEFAULT_REGION, DRY_RUN_YES, DRY_RUN_NO, CURRENT_DATE, DEFAULT_AMI_ID, \
    INSTANCE_TYPE


@mock_ec2
def test_ip_unattached__verify_count_zero_dry_run_yes():
    """
    This method tests ip unattached, get the data and verify counter as 0
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.allocate_address(Domain='vpc')
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0


@mock_ec2
def test_ip_unattached__verify_count_increased_dry_run_no():
    """
    This method tests ip unattached, get the data and verify counter increased to 1
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.allocate_address(Domain='vpc')
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 1


@mock_ec2
def test_ip_unattached__verify_not_delete_on_dry_run_yes():
    """
    This method tests ip unattached, get the data and verify the resource not deleted on dry run yes
    @return:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [
        {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE.__str__()}@7'}
    ]
    ec2_client.allocate_address(Domain='vpc',TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0


@mock_ec2
def test_ip_unattached__verify_delete_on_dry_run_no():
    """
    This method tests ip unattached, deletes the ip
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [
        {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE.__str__()}@7'}
    ]
    ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 0
    assert len(response) == 1
    assert response[0]['ResourceState'] == 'Deleted'


@mock_ec2
def test_ip_unattached__skips_delete_on_dry_run_no():
    """
    This method tests ip unattached, skips delete if tags have Policy=skip
    @return:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [
        {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE.__str__()}@07'},
        {'Key': 'Policy', 'Value': 'skip'},
    ]
    ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 0


@mock_ec2
def test_ip_unattached__skips_active_ip():
    """
    This method tests ip unattached, skips active ip
    @return:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [
        {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE.__str__()}@7'},
        {'Key': 'Policy', 'Value': 'skip'},
    ]
    instance = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE, MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances')[0]
    ip_address = ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    ec2_client.associate_address(AllocationId=ip_address.get('AllocationId'), InstanceId=instance.get('InstanceId'))
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 0


@mock_ec2
def test_ip_unattached__create_run_associate():
    """
    This method tests ip unattached, skips active ip
    @return:
    """
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [
        {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE.__str__()}@0'},
    ]
    instance = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE, MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances')[0]
    ip_address = ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    ec2_client.associate_address(AllocationId=ip_address.get('AllocationId'), InstanceId=instance.get('InstanceId'))
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    addresses = ec2_client.describe_addresses()['Addresses']
    assert len(addresses) == 1
    assert len(response) == 0
