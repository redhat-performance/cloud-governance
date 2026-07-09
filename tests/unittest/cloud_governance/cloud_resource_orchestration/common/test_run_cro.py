from unittest.mock import MagicMock, patch

from cloud_governance.main.environment_variables import environment_variables


@patch('cloud_governance.cloud_resource_orchestration.common.run_cro.CroObject')
@patch('cloud_governance.cloud_resource_orchestration.common.run_cro.ElasticSearchOperations')
def test_send_cro_alerts_handles_es_stored_offset_datetime(mock_es_operations_cls, mock_cro_object_cls):
    """
    Regression test: Elasticsearch returns the previously stored `last_run_<account>`
    timestamp as an ISO string with a timezone offset (e.g. '...+00:00'), since the
    ES client serializes stored `datetime.now(tz=timezone.utc)` objects via isoformat().
    RunCRO must parse this without raising "unconverted data remains: +00:00", and must
    still run the cost-over-usage/ticket-monitoring flow when the stored date differs
    from today.
    """
    from cloud_governance.cloud_resource_orchestration.common.run_cro import RunCRO

    environment_variables.environment_variables_dict['account'] = 'perf-dept'
    environment_variables.environment_variables_dict['PUBLIC_CLOUD_NAME'] = 'AWS'

    mock_es_operations = MagicMock()
    mock_es_operations.get_es_data_by_id.return_value = {
        '_source': {'last_run_perf-dept': '2020-01-01T13:00:23.548397+00:00'}
    }
    mock_es_operations.verify_elastic_index_doc_id.return_value = True
    mock_es_operations_cls.return_value = mock_es_operations

    mock_cost_over_usage = MagicMock()
    mock_cost_over_usage.run.return_value = ['user1']
    mock_monitor_tickets = MagicMock()
    mock_cro_reports = MagicMock()

    mock_cro_object = MagicMock()
    mock_cro_object.cost_over_usage.return_value = mock_cost_over_usage
    mock_cro_object.collect_cro_reports.return_value = mock_cro_reports
    mock_cro_object.monitor_tickets.return_value = mock_monitor_tickets
    mock_cro_object_cls.return_value = mock_cro_object

    run_cro = RunCRO()
    run_cro.run()

    mock_cost_over_usage.run.assert_called_once()
    mock_monitor_tickets.run.assert_called_once()
    mock_cro_reports.update_in_progress_ticket_cost.assert_called_once()


@patch('cloud_governance.cloud_resource_orchestration.common.run_cro.CroObject')
@patch('cloud_governance.cloud_resource_orchestration.common.run_cro.ElasticSearchOperations')
def test_send_cro_alerts_skips_when_already_run_today(mock_es_operations_cls, mock_cro_object_cls):
    """When the stored last_run timestamp is today (still with a timezone offset), the
    alert/ticket-monitoring flow should be skipped rather than re-run."""
    from datetime import datetime, timezone

    from cloud_governance.cloud_resource_orchestration.common.run_cro import RunCRO

    environment_variables.environment_variables_dict['account'] = 'perf-dept'
    environment_variables.environment_variables_dict['PUBLIC_CLOUD_NAME'] = 'AWS'

    today_iso = datetime.now(tz=timezone.utc).isoformat()

    mock_es_operations = MagicMock()
    mock_es_operations.get_es_data_by_id.return_value = {
        '_source': {'last_run_perf-dept': today_iso}
    }
    mock_es_operations.verify_elastic_index_doc_id.return_value = True
    mock_es_operations_cls.return_value = mock_es_operations

    mock_cost_over_usage = MagicMock()
    mock_monitor_tickets = MagicMock()
    mock_cro_reports = MagicMock()

    mock_cro_object = MagicMock()
    mock_cro_object.cost_over_usage.return_value = mock_cost_over_usage
    mock_cro_object.collect_cro_reports.return_value = mock_cro_reports
    mock_cro_object.monitor_tickets.return_value = mock_monitor_tickets
    mock_cro_object_cls.return_value = mock_cro_object

    run_cro = RunCRO()
    run_cro.run()

    mock_cost_over_usage.run.assert_not_called()
    mock_monitor_tickets.run.assert_not_called()
    mock_cro_reports.update_in_progress_ticket_cost.assert_not_called()
