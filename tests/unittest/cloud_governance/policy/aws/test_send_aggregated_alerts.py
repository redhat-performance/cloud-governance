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


def _group_by_user(alert, records: list):
    return alert._SendAggregatedAlerts__group_by_user(policy_data=records)


def _record(**overrides):
    record = {'policy': 'ip_unattached', 'ResourceId': 'eipalloc-123', 'User': 'jdoe'}
    record.update(overrides)
    return record


def test_group_by_user_prefers_email_tag():
    """
    This method tests a valid Email tag routes the digest to the group address instead of
    the individual, which is the point of the whole change.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    grouped = _group_by_user(alert, [_record(Email='team-dl@redhat.com')])
    assert list(grouped.keys()) == ['team-dl@redhat.com']


def test_group_by_user_falls_back_to_user_when_email_missing():
    """
    This method tests an untagged resource routes exactly as it does today
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    grouped = _group_by_user(alert, [_record()])
    assert list(grouped.keys()) == ['jdoe']


def test_group_by_user_falls_back_to_user_when_email_invalid():
    """
    This method tests an Email tag on a disallowed domain does not divert the alert, it
    falls back to the User tag
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    grouped = _group_by_user(alert, [_record(Email='team-dl@gmail.com')])
    assert list(grouped.keys()) == ['jdoe']


def test_group_by_user_drops_records_with_no_routable_recipient():
    """
    This method tests records with neither tag are dropped rather than grouped under 'NA'
    and mailed to NA@redhat.com, which is what happens today for untagged S3 buckets.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    grouped = _group_by_user(alert, [_record(User='NA'), _record(User=''), _record(User=None)])
    assert grouped == {}


def test_group_by_user_routes_access_key_alerts_to_the_individual():
    """
    This method tests access-key alerts ignore the Email tag - a 'your access key will be
    deactivated' notice is a personal credential matter and must not broadcast to a DL.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    records = [
        _record(policy='unused_access_key', Email='team-dl@redhat.com'),
        _record(policy='delete_access_key', Email='team-dl@redhat.com'),
    ]
    grouped = _group_by_user(alert, records)
    assert list(grouped.keys()) == ['jdoe']
    assert len(grouped['jdoe']) == 2


def test_group_by_user_merges_users_sharing_one_group_address():
    """
    This method tests two users pointing at the same group address receive a single
    combined digest rather than one each
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    records = [
        _record(User='jdoe', Email='team-dl@redhat.com'),
        _record(User='asmith', Email='team-dl@redhat.com'),
    ]
    grouped = _group_by_user(alert, records)
    assert list(grouped.keys()) == ['team-dl@redhat.com']
    assert len(grouped['team-dl@redhat.com']) == 2


def test_group_by_user_handles_historical_records_without_email_key():
    """
    This method tests ES documents written before the schema change, which have no Email
    key at all, still route to the User tag
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    alert = _make_alert_instance()
    grouped = _group_by_user(alert, [{'policy': 'ip_unattached', 'ResourceId': 'eipalloc-1', 'User': 'jdoe'}])
    assert list(grouped.keys()) == ['jdoe']


def test_get_greeting_user_returns_the_single_user():
    """
    This method tests a group-routed digest still greets the person by name when the group
    address covers only one user's resources
    """
    alert = _make_alert_instance()
    greeting = alert._SendAggregatedAlerts__get_greeting_user(user_records=[_record(), _record()])
    assert greeting == 'jdoe'


def test_get_greeting_user_is_empty_when_the_group_spans_several_users():
    """
    This method tests no single person is greeted when a group address covers several
    users' resources, so the template falls back to a generic greeting
    """
    alert = _make_alert_instance()
    records = [_record(User='jdoe'), _record(User='asmith')]
    assert alert._SendAggregatedAlerts__get_greeting_user(user_records=records) == ''


def test_send_aggregate_email_mails_the_group_address_and_greets_the_user():
    """
    This method tests the end-to-end routing: the mail is addressed to the Email tag while
    the greeting still resolves the User tag, so the recipient changes but the salutation
    does not become a group address.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    environment_variables.environment_variables_dict['ADMIN_MAIL_LIST'] = ''
    alert = _make_alert_instance()
    alert._SendAggregatedAlerts__environment_variables = environment_variables.environment_variables_dict
    alert._SendAggregatedAlerts__mail_message = MagicMock()
    alert._SendAggregatedAlerts__mail_message.get_policy_alert_message.return_value = ('subject', 'body')
    alert._SendAggregatedAlerts__postfix = MagicMock()
    records = [_record(DryRun='yes', Email='team-dl@redhat.com')]
    with patch.object(SendAggregatedAlerts, '_SendAggregatedAlerts__get_es_data', return_value=records):
        alert._SendAggregatedAlerts__send_aggregate_email_by_es_data()
    _, mail_kwargs = alert._SendAggregatedAlerts__mail_message.get_policy_alert_message.call_args
    assert mail_kwargs['user'] == 'jdoe'
    _, postfix_kwargs = alert._SendAggregatedAlerts__postfix.send_email_postfix.call_args
    assert postfix_kwargs['to'] == 'team-dl@redhat.com'
