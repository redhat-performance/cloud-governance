from datetime import datetime, timedelta

import boto3
from moto import mock_ec2, mock_s3, mock_iam

from cloud_governance.common.helpers.aws.aws_cleanup_operations import AWSCleanUpOperations
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.ec2_run import EC2Run


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data[0].get('ResourceStopped') == 'False'
    assert running_instances_data[0].get('InstanceState') == 'running'


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run_alert():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'running',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 1,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'False'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1



@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run_alert_stopped():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'stopped',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'True'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run_alert_skip():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}, {'Key': "Skip", "Value": f"notdelete"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NOTDELETE',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'running',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'False'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run_stop_reset():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'stopped',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'True'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0
    ec2_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    aws_cleanup_operations = AWSCleanUpOperations()
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '0'


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_run_stop_start():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'stopped',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'True'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0
    ec2_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    aws_cleanup_operations = AWSCleanUpOperations()
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '0'
    ec2_client.start_instances(InstanceIds=[resource.get('InstanceId')])
    ec2_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '1'


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_force_delete():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['FORCE_DELETE'] = True
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    environment_variables.environment_variables_dict['RESOURCE_ID'] = resource.get('InstanceId')
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'stopped',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'no',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'True',
            'ForceDeleted': 'True'
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_force_delete_skip():
    """
    This method tests ec2_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['FORCE_DELETE'] = True
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get(
        'Instances',
        [])
    resource = resource[0]
    environment_variables.environment_variables_dict['RESOURCE_ID'] = resource.get('InstanceId')
    ec2_run = EC2Run()
    running_instances_data = ec2_run.run()
    assert running_instances_data == [
        {
            'ResourceId': resource.get('InstanceId'),
            'User': 'cloud-governance',
            'SkipPolicy': 'NA',
            'LaunchTime': resource['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            'InstanceType': resource.get('InstanceType'),
            'InstanceState': 'running',
            'StateTransitionReason': resource.get('StateTransitionReason'),
            'RunningDays': 0,
            'CleanUpDays': 4,
            'DryRun': 'yes',
            'Name': 'Unittest',
            'RegionName': 'ap-south-1',
            'ResourceStopped': 'False',
        }
    ]
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1
