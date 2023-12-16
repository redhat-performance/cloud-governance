import datetime

import boto3
from moto import mock_ec2, mock_s3, mock_iam

from cloud_governance.common.helpers.aws.aws_cleanup_operations import AWSCleanUpOperations
from cloud_governance.main.environment_variables import environment_variables


@mock_ec2
@mock_s3
@mock_iam
def test_get_tag_name_from_tags():
    """
    This method tests get_tag_name_from_tags method
    :return:
    :rtype:
    """
    aws_cleanup_operations = AWSCleanUpOperations()
    tags = [{'Key': "Name", "Value": "Unittest"}]
    tag_value = aws_cleanup_operations.get_tag_name_from_tags(tags=tags, tag_name="Name")
    assert tag_value == "Unittest"


@mock_ec2
@mock_s3
@mock_iam
def test_get_clean_up_days_count():
    """
    This method tests get_clean_up_days_count method
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    aws_cleanup_operations = AWSCleanUpOperations()
    tags = [{'Key': "Name", "Value": "Unittest"}]
    days_count = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert days_count == 1


@mock_ec2
@mock_s3
@mock_iam
def test_get_clean_up_days_count_already_exists():
    """
    This method tests get_clean_up_days_count method
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    aws_cleanup_operations = AWSCleanUpOperations()
    mock_date = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).date()
    tags = [{'Key': "Name", "Value": "Unittest"}, {'Key': "DaysCount", "Value": f'{mock_date}@1'}]
    days_count = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert days_count == 2


@mock_ec2
@mock_s3
@mock_iam
def test_get_clean_up_days_count_already_updated_today():
    """
    This method tests get_clean_up_days_count method
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    aws_cleanup_operations = AWSCleanUpOperations()
    mock_date = str(datetime.datetime.utcnow().date())
    tags = [{'Key': "Name", "Value": "Unittest"}, {'Key': "DaysCount", "Value": f'{mock_date}@1'}]
    days_count = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
    assert days_count == 1


@mock_ec2
@mock_s3
@mock_iam
def test_get_skip_policy_value_policy_tag():
    """
    This method tests get_skip_policy_value
    :return:
    :rtype:
    """
    aws_cleanup_operations = AWSCleanUpOperations()
    tags = [{'Key': "Name", "Value": "Unittest"},
            {'Key': "Policy", "Value": "NotDelete"}]
    tag_value = aws_cleanup_operations.get_skip_policy_value(tags=tags)
    assert tag_value == "NotDelete".upper()


@mock_ec2
@mock_s3
@mock_iam
def test_get_skip_policy_value_skip_tag():
    """
    This method tests get_skip_policy_value
    :return:
    :rtype:
    """
    aws_cleanup_operations = AWSCleanUpOperations()
    tags = [{'Key': "Name", "Value": "Unittest"},
            {'Key': "Skip", "Value": "NotDelete"}]
    tag_value = aws_cleanup_operations.get_skip_policy_value(tags=tags)
    assert tag_value == "NotDelete".upper()


@mock_ec2
@mock_s3
@mock_iam
def test_delete_resource():
    """
    This method tests _delete_resource
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances', [])
    if resource:
        resource_id = resource[0].get('InstanceId')
        aws_cleanup_operations = AWSCleanUpOperations()
        aws_cleanup_operations._delete_resource(resource_id=resource_id)
        assert len(ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])['Reservations']) == 0


@mock_ec2
@mock_s3
@mock_iam
def test_update_resource_day_count_tag():
    """
    This method tests update_resource_day_count_tag
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    if resource:
        resource_id = resource[0].get('InstanceId')
        aws_cleanup_operations = AWSCleanUpOperations()
        cleanup_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
        aws_cleanup_operations.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)
        instances = ec2_client.describe_instances()['Reservations']
        tag_value = aws_cleanup_operations.get_tag_name_from_tags(instances[0]['Instances'][0].get('Tags'), tag_name='DaysCount')
        assert tag_value == str(datetime.datetime.utcnow().date()) + "@0"


@mock_ec2
@mock_s3
@mock_iam
def test_update_resource_day_count_tag_exists_tag():
    """
    This method tests update_resource_tags
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DaysCount", "Value": f'{mock_date}@1'}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    if resource:
        resource_id = resource[0].get('InstanceId')
        aws_cleanup_operations = AWSCleanUpOperations()
        cleanup_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
        aws_cleanup_operations.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)
        instances = ec2_client.describe_instances()['Reservations']
        tag_value = aws_cleanup_operations.get_tag_name_from_tags(instances[0]['Instances'][0].get('Tags'), tag_name='DaysCount')
        assert tag_value == str(datetime.datetime.utcnow().date()) + "@2"


@mock_ec2
@mock_s3
@mock_iam
def test_update_resource_day_count_tag_updated_tag_today():
    """
    This method tests update_resource_tags
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['policy'] = 'ec2_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = 'ap-south-1'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    default_ami_id = 'ami-03cf127a'
    mock_date = datetime.datetime.utcnow().date()
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}, {'Key': "Name", "Value": "Unittest"},
            {'Key': "DryRunYesDays", "Value": f'{mock_date}@1'}]
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}]).get('Instances',
                                                                                                            [])
    if resource:
        resource_id = resource[0].get('InstanceId')
        aws_cleanup_operations = AWSCleanUpOperations()
        cleanup_days = aws_cleanup_operations.get_clean_up_days_count(tags=tags)
        aws_cleanup_operations.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)
        instances = ec2_client.describe_instances()['Reservations']
        tag_value = aws_cleanup_operations.get_tag_name_from_tags(instances[0]['Instances'][0].get('Tags'), tag_name='DaysCount')
        assert tag_value == str(datetime.datetime.utcnow().date()) + "@1"

