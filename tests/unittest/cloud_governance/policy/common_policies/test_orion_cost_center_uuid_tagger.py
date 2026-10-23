from datetime import date
from unittest.mock import patch, MagicMock

from cloud_governance.policy.common_policies.orion_cost_center_uuid_tagger import OrionCostCenterUuidTagger


def _make_tagger(env_overrides=None):
    base_env = {
        'es_host': 'localhost',
        'es_port': '9200',
        'orion_cost_center': '9999',
    }
    if env_overrides:
        base_env.update(env_overrides)
    with patch('cloud_governance.policy.common_policies.orion_cost_center_uuid_tagger.environment_variables') as mock_env, \
         patch('cloud_governance.policy.common_policies.orion_cost_center_uuid_tagger.ElasticSearchOperations') as mock_es_ops:
        mock_env.environment_variables_dict = base_env
        mock_es_instance = MagicMock()
        mock_es_ops.return_value = mock_es_instance
        tagger = OrionCostCenterUuidTagger()
        return tagger, mock_es_instance


def test_run_skips_when_es_not_configured():
    tagger, _ = _make_tagger({'es_host': ''})
    result = tagger.run()
    assert result['status'] == 'no_upload'


def test_run_skips_when_cost_center_not_configured():
    tagger, _ = _make_tagger({'orion_cost_center': ''})
    result = tagger.run()
    assert result['status'] == 'skipped'


def test_build_query_filters_on_cost_center_policies_and_actual():
    tagger, _ = _make_tagger()
    query = tagger._OrionCostCenterUuidTagger__build_query(start_date='2026-09-01', end_date='2026-09-30')
    filters = query['bool']['filter']
    assert {"term": {"CostCenter": 9999}} in filters
    assert {"terms": {"policy.keyword": ['cost_explorer_payer_billings', 'cost_billing_reports']}} in filters
    assert {"range": {"Actual": {"gt": 0}}} in filters
    assert {"range": {"start_date": {"gte": "2026-09-01", "lte": "2026-09-30", "format": "yyyy-MM-dd"}}} in filters


def test_build_script_sets_account_and_orion_uuid_from_param():
    script = OrionCostCenterUuidTagger._OrionCostCenterUuidTagger__build_script(9999)
    assert script['params'] == {'cost_center': 9999}
    assert "ctx._source.account = 'CC' + params.cost_center" in script['source']
    assert "ctx._source.orion_uuid = 'CC' + params.cost_center" in script['source']
    assert "substring(0, 7)" in script['source']


def test_build_script_normalizes_legacy_awscloud_label():
    script = OrionCostCenterUuidTagger._OrionCostCenterUuidTagger__build_script(9999)
    assert "ctx._source.CloudName == 'AWSCLOUD'" in script['source']
    assert "ctx._source.CloudName = 'AWS'" in script['source']


def test_run_incremental_mode_uses_last_completed_month():
    tagger, mock_es = _make_tagger()
    mock_es.update_by_query.return_value = {'updated': 3}
    with patch('cloud_governance.policy.common_policies.orion_cost_center_uuid_tagger.datetime') as mock_dt:
        mock_dt.now.return_value.date.return_value = date(2026, 10, 15)
        result = tagger.run()
    assert result['status'] == 'success'
    assert result['start_date'] == '2026-09-01'
    assert result['end_date'] == '2026-09-30'
    assert result['documents_tagged'] == 3


def test_run_backfill_with_explicit_args():
    tagger, mock_es = _make_tagger()
    mock_es.update_by_query.return_value = {'updated': 42}
    result = tagger.run(start_date='2023-03-01', end_date='2026-10-01')
    assert result['status'] == 'success'
    assert result['start_date'] == '2023-03-01'
    assert result['end_date'] == '2026-10-01'
    assert result['documents_tagged'] == 42
    mock_es.update_by_query.assert_called_once()
    call_kwargs = mock_es.update_by_query.call_args.kwargs
    assert call_kwargs['es_index'] == 'cloud-governance-clouds-billing-reports'


def test_run_reports_partial_failure_on_version_conflicts():
    tagger, mock_es = _make_tagger()
    mock_es.update_by_query.return_value = {'updated': 2, 'version_conflicts': 1, 'failures': []}
    result = tagger.run(start_date='2026-09-01', end_date='2026-09-30')
    assert result['status'] == 'partial_failure'
    assert result['version_conflicts'] == 1


def test_run_falls_back_to_incremental_on_partial_date_args():
    tagger, mock_es = _make_tagger()
    mock_es.update_by_query.return_value = {'updated': 1}
    with patch('cloud_governance.policy.common_policies.orion_cost_center_uuid_tagger.datetime') as mock_dt:
        mock_dt.now.return_value.date.return_value = date(2026, 10, 15)
        result = tagger.run(start_date='2023-03-01', end_date=None)
    assert result['start_date'] == '2026-09-01'
    assert result['end_date'] == '2026-09-30'
