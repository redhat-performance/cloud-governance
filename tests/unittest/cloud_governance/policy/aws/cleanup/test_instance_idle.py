from datetime import datetime, timedelta
from typing import Union
from unittest.mock import patch

import boto3
from moto import mock_ec2, mock_cloudwatch

from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.instance_idle import InstanceIdle
from tests.unittest.configs import AWS_DEFAULT_REGION, DRY_RUN_YES, DEFAULT_AMI_ID, INSTANCE_TYPE_T2_MICRO, \
    TEST_USER_NAME, DRY_RUN_NO, CURRENT_DATE


@mock_cloudwatch
@mock_ec2
def test_instance_idle__instance_age_less_than_7():
    """
    This method tests instance_idle of less than DEFAULT_DAYs 7
    :return:
    :rtype:
    """

    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}]
    ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO, MaxCount=1,
                             MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 0
    assert not get_tag_value_from_tags(instance_idle._get_all_instances()[0]['Tags'], tag_name='cost-savings')


def mock_describe_instances(*args, **kwargs):
    mock_response = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-1234567890abcdef0',
                        'State': {'Name': 'running'},
                        'LaunchTime': kwargs.get('LaunchTime', datetime.utcnow()),
                        'Tags': kwargs.get('Tags', []),
                        'PlatformDetails': 'Linux/UNIX'
                        # Change the launch time here
                    }
                ]
            }
        ]
    }
    return mock_response


class MockCloudWatchMetric:

    def __init__(self, metrics: Union[int, float, list]):
        self.__metrics = metrics

    def create_metric(self, *args, **kwargs):
        return {
            'MetricDataResults': [
                {
                    'Values': self.__metrics if isinstance(self.__metrics, list) else [self.__metrics]
                }
            ]
        }


def test_instance_idle__check_not_idle():
    """
    This method tests instance_idle, check for not idle instances
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(LaunchTime=datetime.utcnow() - timedelta(days=8))]
        mock_client.return_value.get_metric_data.side_effect = [
            MockCloudWatchMetric(metrics=[5, 4, 8, 10]).create_metric(),
            MockCloudWatchMetric(metrics=[5000, 2000, 4000, 8000]).create_metric(),
            MockCloudWatchMetric(metrics=[1000, 200, 500]).create_metric()
        ]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 0


def test_instance_idle__skip_cluster():
    """
    This method tests instance_idle not collect the active cluster resources
    :return:
    :rtype:
    """
    tags = [{'Key': 'kubernetes.io/cluster/unittest-vm', 'Value': 'owned'}]
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(Tags=tags, LaunchTime=datetime.utcnow() - timedelta(days=8))]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 0


def test_instance_idle__dryrun_no_active_instance():
    """
    This method tests instance_idle dry_run no with non-idle instances
    :return:
    :rtype:
    """
    tags = [{'Key': 'kubernetes.io/cluster/unittest-vm', 'Value': 'owned'}]
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(Tags=tags, LaunchTime=datetime.utcnow() - timedelta(days=8))]
        mock_client.return_value.get_metric_data.side_effect = [
            MockCloudWatchMetric(metrics=[5, 4, 8, 10]).create_metric(),
            MockCloudWatchMetric(metrics=[5000, 2000, 4000, 8000]).create_metric(),
            MockCloudWatchMetric(metrics=[1000, 200, 500]).create_metric()
        ]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 0


def test_instance_idle__dryrun_no_delete():
    """
    This method tests stop the instance_idle
    :return:
    :rtype:
    """
    tags = [{'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(Tags=tags, LaunchTime=datetime.utcnow() - timedelta(days=8))]
        mock_client.return_value.get_metric_data.side_effect = [
            MockCloudWatchMetric(metrics=[0, 1, 0, 0.1]).create_metric(),
            MockCloudWatchMetric(metrics=[50, 20, 5, 10]).create_metric(),
            MockCloudWatchMetric(metrics=[5, 3, 100]).create_metric()
        ]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 1
        assert response[0]['CleanUpDays'] == 7
        assert response[0]['ResourceState'] == 'Stop'


def test_instance_idle__skips_delete():
    """
    This method tests skip deletion of instance_idle
    :return:
    :rtype:
    """
    tags = [{'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'},
            {'Key': 'Policy', 'Value': 'skip'}]
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(Tags=tags, LaunchTime=datetime.utcnow() - timedelta(days=8))]
        mock_client.return_value.get_metric_data.side_effect = [
            MockCloudWatchMetric(metrics=[0, 1, 0, 0.1]).create_metric(),
            MockCloudWatchMetric(metrics=[50, 20, 5, 10]).create_metric(),
            MockCloudWatchMetric(metrics=[5, 3, 100]).create_metric()
        ]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 0


def test_instance_idle__set_counter_zero():
    """
    This method tests  unused_nat_gateway to set days counter to 0
    :return:
    :rtype:
    """
    tags = [{'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.side_effect = [
            mock_describe_instances(Tags=tags, LaunchTime=datetime.utcnow() - timedelta(days=8))]
        mock_client.return_value.get_metric_data.side_effect = [
            MockCloudWatchMetric(metrics=[0, 1, 0, 0.1]).create_metric(),
            MockCloudWatchMetric(metrics=[50, 20, 5, 10]).create_metric(),
            MockCloudWatchMetric(metrics=[5, 3, 100]).create_metric()
        ]
        instance_idle = InstanceIdle()
        response = instance_idle.run()
        assert len(response) == 1
        assert response[0]['CleanUpDays'] == 0
