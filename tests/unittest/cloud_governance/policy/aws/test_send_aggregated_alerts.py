from unittest.mock import patch, MagicMock

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.common_policies.send_aggregated_alerts import SendAggregatedAlerts


def _make_alert_instance():
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    environment_variables.environment_variables_dict['EMAIL_TO'] = ''
    environment_variables.environment_variables_dict['EMAIL_CC'] = []
    environment_variables.environment_variables_dict['ALERT_DRY_RUN'] = 'yes'
    environment_variables.environment_variables_dict['SKIP_POLICIES_ALERT'] = []
    with patch.object(SendAggregatedAlerts, '__init__', lambda self: None):
        alert = SendAggregatedAlerts()
        alert._SendAggregatedAlerts__alert_dry_run = 'yes'
        alert._SendAggregatedAlerts__days_to_delete_resource = 7
    return alert


def test_update_delete_days_uses_cleanup_days_over_cluster_resources_count():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 4,
        'ClusterResourcesCount': 1,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1
    assert result[0]['DeleteDate'] != ''


def test_update_delete_days_cluster_resources_count_alone_still_works():
    alert = _make_alert_instance()
    record = {
        'ClusterResourcesCount': 4,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1
    assert result[0]['DeleteDate'] != ''


def test_update_delete_days_falls_through_to_days():
    alert = _make_alert_instance()
    record = {
        'Days': 2,
        'DryRun': 'no',
        'policy': 'instance_idle',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1


def test_update_delete_days_falls_through_to_stopped_days():
    alert = _make_alert_instance()
    record = {
        'StoppedDays': 2,
        'DryRun': 'no',
        'policy': 'ec2_stop',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1


def test_update_delete_days_dry_run_yes_always_included():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 1,
        'DryRun': 'yes',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1
    assert result[0]['DeleteDate'] == 'dry_run=yes'


def test_update_delete_days_first_alert_threshold():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 2,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1
    assert result[0].get('DeleteDate') != ''


def test_update_delete_days_second_alert_threshold():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 4,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1


def test_update_delete_days_deletion_threshold():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 7,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 1


def test_update_delete_days_no_alert_between_thresholds():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 3,
        'DryRun': 'no',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 0


def test_update_delete_days_skip_policy_gets_skip_delete():
    alert = _make_alert_instance()
    record = {
        'CleanUpDays': 3,
        'DryRun': 'no',
        'SkipPolicy': 'NOTDELETE',
        'policy': 'zombie_cluster_resource',
    }
    result = alert._SendAggregatedAlerts__update_delete_days([record])
    assert len(result) == 0
