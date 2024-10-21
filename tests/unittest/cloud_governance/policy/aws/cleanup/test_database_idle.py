from datetime import datetime, timedelta

from freezegun import freeze_time
from moto import mock_rds, mock_cloudwatch

from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client, get_tag_value_from_tags
from cloud_governance.policy.aws.cleanup.database_idle import DatabaseIdle
from cloud_governance.main.environment_variables import environment_variables
from tests.unittest.configs import DB_INSTANCE_CLASS, AWS_DEFAULT_REGION, TEST_USER_NAME, DB_ENGINE, \
    CLOUD_WATCH_METRICS_DAYS, PROJECT_NAME

current_date = datetime.utcnow()
start_date = current_date - timedelta(days=CLOUD_WATCH_METRICS_DAYS + 1)


@mock_cloudwatch
@mock_rds
@freeze_time(start_date.__str__())
def test_database_idle():
    """
    This method tests database_idle resources
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['policy'] = 'database_idle'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    rds_client = get_boto3_client('rds', region_name=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': PROJECT_NAME}, {'Key': "Name", "Value": TEST_USER_NAME}]
    rds_client.create_db_instance(DBInstanceIdentifier=TEST_USER_NAME,
                                  DBInstanceClass=DB_INSTANCE_CLASS,
                                  Engine=DB_ENGINE, Tags=tags)
    database_idle = DatabaseIdle()
    running_instances_data = database_idle.run()
    assert len(running_instances_data) == 1
    assert get_tag_value_from_tags(tags=rds_client.describe_db_instances()['DBInstances'][0]['TagList'],
                                   tag_name='DaysCount') == f"{current_date.date()}@1"
    assert get_tag_value_from_tags(tags=rds_client.describe_db_instances()['DBInstances'][0]['TagList'],
                                   tag_name='cost-savings') == "true"


@mock_cloudwatch
@mock_rds
@freeze_time(start_date.__str__())
def test_database_idle_alert_skip():
    """
    This method tests database_idle skip delete
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'database_idle'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    rds_client = get_boto3_client('rds', region_name=AWS_DEFAULT_REGION)
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': PROJECT_NAME}, {'Key': "Name", "Value": TEST_USER_NAME},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}, {'Key': "Skip", "Value": f"notdelete"}]
    rds_client.create_db_instance(DBInstanceIdentifier=TEST_USER_NAME,
                                  DBInstanceClass=DB_INSTANCE_CLASS,
                                  Engine=DB_ENGINE, Tags=tags)
    database_idle = DatabaseIdle()
    running_instances_data = database_idle.run()
    assert len(running_instances_data) == 0
    assert len(rds_client.describe_db_instances()['DBInstances']) == 1


@mock_cloudwatch
@mock_rds
@freeze_time(start_date.__str__())
def test_database_idle_delete():
    """
    This method tests the deletion of database_idle
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'database_idle'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    rds_client = get_boto3_client('rds', region_name=AWS_DEFAULT_REGION)
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': PROJECT_NAME}, {'Key': "Name", "Value": TEST_USER_NAME},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    rds_client.create_db_instance(DBInstanceIdentifier=TEST_USER_NAME,
                                  DBInstanceClass=DB_INSTANCE_CLASS,
                                  Engine=DB_ENGINE, Tags=tags)
    database_idle = DatabaseIdle()
    running_instances_data = database_idle.run()
    assert running_instances_data[0]['DryRun'] == 'no'
    assert running_instances_data[0]['ResourceAction'] == 'True'


@mock_cloudwatch
@mock_rds
@freeze_time(start_date.__str__())
def test_database_idle_dry_run_yes():
    """
    This method tests the deletion of database_idle
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 2
    environment_variables.environment_variables_dict['policy'] = 'database_idle'
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    rds_client = get_boto3_client('rds', region_name=AWS_DEFAULT_REGION)
    mock_date = (datetime.now() - timedelta(days=2)).date()
    tags = [{'Key': 'User', 'Value': PROJECT_NAME}, {'Key': "Name", "Value": TEST_USER_NAME},
            {'Key': "DaysCount", "Value": f"{mock_date}@3"}]
    rds_client.create_db_instance(DBInstanceIdentifier=TEST_USER_NAME,
                                  DBInstanceClass=DB_INSTANCE_CLASS,
                                  Engine=DB_ENGINE, Tags=tags)
    database_idle = DatabaseIdle()
    running_instances_data = database_idle.run()
    assert running_instances_data[0]['DryRun'] == 'yes'
    assert running_instances_data[0]['ResourceAction'] == 'False'
    assert get_tag_value_from_tags(tags=rds_client.describe_db_instances()['DBInstances'][0]['TagList'],
                                   tag_name='DaysCount') == f"{current_date.date()}@0"
