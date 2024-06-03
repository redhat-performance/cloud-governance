from datetime import datetime, timedelta

import boto3
from moto import mock_ec2, mock_s3, mock_iam

from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.instance_run import InstanceRun


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0].get('ResourceStopped') == 'False'
    assert running_instances_data[0].get('ResourceState') == 'running'


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run_alert():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert len(running_instances_data) == 1
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'False'
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run_alert_stopped():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'True'
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run_alert_skip():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'False'
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run_stop_reset():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'True'
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0
    instance_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    aws_cleanup_operations = AWSPolicyOperations()
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '0'


@mock_ec2
@mock_s3
@mock_iam
def test_instance_run_stop_start():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'True'
    assert running_instances_data[0]['CleanUpDays'] == 4
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0
    instance_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    aws_cleanup_operations = AWSPolicyOperations()
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '0'
    ec2_client.start_instances(InstanceIds=[resource.get('InstanceId')])
    instance_run.run()
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']
    instances = instances[0]['Instances'][0]
    assert aws_cleanup_operations.get_tag_name_from_tags(tags=instances.get('Tags'), tag_name='DaysCount').split('@')[-1] == '1'


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_force_delete():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['FORCE_DELETE'] = True
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceStopped'] == 'True'
    assert running_instances_data[0]['ForceDeleted'] == 'True'
    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_ec2_force_delete_skip():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['FORCE_DELETE'] = True
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
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
    instance_run = InstanceRun()
    running_instances_data = instance_run.run()
    assert running_instances_data[0]['ResourceId'] == resource.get('InstanceId')
    assert running_instances_data[0]['DryRun'] == 'yes'
    assert running_instances_data[0]['ResourceStopped'] == 'False'

    assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 1
