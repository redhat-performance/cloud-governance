import datetime
from unittest.mock import patch

from freezegun import freeze_time
from moto import mock_aws

from cloud_governance.policy.aws.monitor.cluster_run import ClusterRun
from cloud_governance.main.environment_variables import environment_variables

AWS_DEFAULT_REGION = 'us-east-1'
CLUSTER_TAG = 'kubernetes.io/cluster/unittest-cluster'
UNIT_PRICE = 0.1
FROZEN_NOW = datetime.datetime(2026, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _build_instance(launch_time, state='running', stopped_at=None, instance_type='m5.xlarge'):
    """
    This method builds a describe_instances style payload for the policy to consume.
    :return:
    :rtype:
    """
    instance = {
        'InstanceId': 'i-0123456789abcdef0',
        'InstanceType': instance_type,
        'LaunchTime': launch_time,
        'State': {'Name': state},
        'Tags': [{'Key': CLUSTER_TAG, 'Value': 'owned'},
                 {'Key': 'Name', 'Value': 'unittest-cluster-worker'},
                 {'Key': 'User', 'Value': 'cloud-governance'}],
        'BlockDeviceMappings': [],
    }
    if stopped_at:
        instance['StateTransitionReason'] = f"User initiated ({stopped_at.strftime('%Y-%m-%d %H:%M:%S')} GMT)"
    return instance


def _run_cluster_run(instances: list):
    """
    This method runs the cluster_run policy against a fixed instance list and price.
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['policy'] = 'cluster_run'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    cluster_run = ClusterRun()
    with patch.object(cluster_run, '_get_all_instances', return_value=instances), \
            patch.object(cluster_run._resource_pricing, 'get_ec2_price', return_value=UNIT_PRICE):
        return cluster_run.run_policy_operations()


@mock_aws
@freeze_time(FROZEN_NOW)
def test_cluster_run_running_hours_include_whole_days():
    """
    This method tests a running cluster reports every elapsed hour.
    Guards against timedelta.seconds, which drops the days component and caps
    RunningHours at 24 however old the cluster is.
    :return:
    :rtype:
    """
    launch_time = FROZEN_NOW - datetime.timedelta(days=30)
    clusters = _run_cluster_run([_build_instance(launch_time)])
    assert len(clusters) == 1
    assert clusters[0]['RunningDays'] == 30
    assert clusters[0]['RunningHours'] == 30 * 24
    assert clusters[0]['TotalCost'] == round(UNIT_PRICE * 30 * 24, 3)


@mock_aws
@freeze_time(FROZEN_NOW)
def test_cluster_run_stopped_excludes_the_stopped_period():
    """
    This method tests a stopped cluster is measured launch -> stopped, not
    launch -> now, so the time it spent stopped is not billed.
    :return:
    :rtype:
    """
    launch_time = FROZEN_NOW - datetime.timedelta(days=210)
    stopped_at = launch_time + datetime.timedelta(days=30)
    clusters = _run_cluster_run([_build_instance(launch_time, state='stopped', stopped_at=stopped_at)])
    assert len(clusters) == 1
    # ran for 30 days, then sat stopped for 180
    assert clusters[0]['RunningDays'] == 30
    assert clusters[0]['RunningHours'] == 30 * 24
    assert clusters[0]['TotalCost'] == round(UNIT_PRICE * 30 * 24, 3)


@mock_aws
@freeze_time(FROZEN_NOW)
def test_cluster_run_stopped_days_are_not_negative():
    """
    This method tests the stopped branch reports a positive duration.
    Guards against the reversed argument order, which returned launch - stopped.
    :return:
    :rtype:
    """
    launch_time = FROZEN_NOW - datetime.timedelta(days=74)
    stopped_at = FROZEN_NOW - datetime.timedelta(days=14)
    clusters = _run_cluster_run([_build_instance(launch_time, state='stopped', stopped_at=stopped_at)])
    assert clusters[0]['RunningDays'] == 60


@mock_aws
@freeze_time(FROZEN_NOW)
def test_cluster_run_cost_stays_positive_on_clock_skew():
    """
    This method tests a launch time ahead of the current clock cannot produce a
    negative cost. ceil() of a negative hour count is negative, so an equality
    check against zero does not catch it.
    :return:
    :rtype:
    """
    launch_time = FROZEN_NOW + datetime.timedelta(hours=3)
    clusters = _run_cluster_run([_build_instance(launch_time)])
    assert clusters[0]['TotalCost'] > 0
