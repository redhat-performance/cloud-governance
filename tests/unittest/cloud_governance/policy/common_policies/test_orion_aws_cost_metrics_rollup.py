import datetime
from unittest.mock import patch, MagicMock

from cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup import OrionAwsCostMetricsRollup


class TestOrionAwsCostMetricsRollup:
    """Test suite for OrionAwsCostMetricsRollup class"""

    def _make_rollup(self, env_overrides=None):
        base_env = {
            'es_host': 'localhost',
            'es_port': '9200',
        }
        if env_overrides:
            base_env.update(env_overrides)
        with patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.environment_variables') as mock_env, \
             patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.ElasticSearchOperations') as mock_es_ops:
            mock_env.environment_variables_dict = base_env
            mock_es_instance = MagicMock()
            mock_es_ops.return_value = mock_es_instance
            rollup = OrionAwsCostMetricsRollup()
            rollup._mock_es = mock_es_instance
            return rollup

    def setup_method(self):
        self.rollup = self._make_rollup()
        self.mock_es_instance = self.rollup._mock_es

    def _agg(self, buckets):
        return {'by_day': {'buckets': buckets}}

    def test_build_query_filters_accounts_tag_and_savings_plan(self):
        """Query must scope to the 3 tracked accounts and pin exactly one (tag, savings_plan) pair"""
        query = self.rollup._OrionAwsCostMetricsRollup__build_query('2026-01-01', '2026-01-31')
        filters = query['query']['bool']['filter']

        accounts = [f for f in filters if 'terms' in f and 'account.keyword' in f.get('terms', {})]
        assert set(accounts[0]['terms']['account.keyword']) == set(OrionAwsCostMetricsRollup.ACCOUNTS)

        tag = [f for f in filters if 'term' in f and 'tag.keyword' in f.get('term', {})]
        assert tag[0]['term']['tag.keyword'] == OrionAwsCostMetricsRollup.CANONICAL_TAG

        savings_plan = [f for f in filters if 'term' in f and 'savings_plan.keyword' in f.get('term', {})]
        assert savings_plan[0]['term']['savings_plan.keyword'] == OrionAwsCostMetricsRollup.CANONICAL_SAVINGS_PLAN

        date_range = [f for f in filters if 'range' in f and 'timestamp' in f.get('range', {})]
        assert date_range[0]['range']['timestamp'] == {'gte': '2026-01-01', 'lte': '2026-01-31', 'format': 'yyyy-MM-dd'}

        # daily buckets
        assert query['aggs']['by_day']['date_histogram']['calendar_interval'] == 'day'

    def test_parse_response_builds_per_account_per_day_docs_rounded(self):
        """One doc per account per day present, rounded to int, uuid = <account>-<date>"""
        response = self._agg([
            {
                'key_as_string': '2026-09-28',
                'by_account': {'buckets': [
                    {'key': 'PERFSCALE', 'spend': {'value': 157.4}},
                    {'key': 'PSAP', 'spend': {'value': 5.2}},
                ]}
            }
        ])
        docs = self.rollup._OrionAwsCostMetricsRollup__parse_response(response)

        assert len(docs) == 2
        by_account = {d['account']: d for d in docs}
        assert by_account['PERFSCALE']['total_cost'] == 157
        assert by_account['PERFSCALE']['timestamp'] == '2026-09-28T00:00:00Z'
        assert by_account['PERFSCALE']['uuid'] == 'PERFSCALE-2026-09-28'
        assert by_account['PSAP']['total_cost'] == 5
        assert all(isinstance(d['total_cost'], int) for d in docs)

    def test_parse_response_skips_unknown_accounts(self):
        """A stray/legacy account (e.g. the dead PERF-SCALE spelling) must not produce a doc"""
        response = self._agg([
            {
                'key_as_string': '2026-01-15',
                'by_account': {'buckets': [
                    {'key': 'PERF-SCALE', 'spend': {'value': 999}},
                    {'key': 'PERFSCALE', 'spend': {'value': 10}},
                ]}
            }
        ])
        docs = self.rollup._OrionAwsCostMetricsRollup__parse_response(response)
        assert len(docs) == 1
        assert docs[0]['account'] == 'PERFSCALE'

    def test_parse_response_missing_account_day_produces_no_doc(self):
        """A day with zero matching docs for an account yields no bucket, and no doc - not a zero"""
        response = self._agg([
            {'key_as_string': '2026-02-01', 'by_account': {'buckets': [{'key': 'PSAP', 'spend': {'value': 12}}]}}
        ])
        docs = self.rollup._OrionAwsCostMetricsRollup__parse_response(response)
        assert len(docs) == 1
        assert {d['account'] for d in docs} == {'PSAP'}

    def test_parse_response_handles_missing_aggregations(self):
        assert self.rollup._OrionAwsCostMetricsRollup__parse_response({}) == []
        assert self.rollup._OrionAwsCostMetricsRollup__parse_response(None) == []

    @patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.OrionAwsCostMetricsRollup._OrionAwsCostMetricsRollup__today')
    def test_trailing_window_lags_and_spans_rolling_window(self, mock_today):
        """Window ends LAG_DAYS before today and spans ROLLING_WINDOW_DAYS days"""
        mock_today.return_value = datetime.date(2026, 10, 1)
        start, end = self.rollup._OrionAwsCostMetricsRollup__trailing_window()
        assert end == '2026-09-28'  # 2026-10-01 - 3 days
        assert start == '2026-08-29'  # 31-day window ending 2026-09-28

    @patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.OrionAwsCostMetricsRollup._OrionAwsCostMetricsRollup__today')
    def test_clamp_end_date_caps_at_lag_boundary(self, mock_today):
        mock_today.return_value = datetime.date(2026, 10, 1)
        # requested end_date is within the safe window - unchanged
        assert self.rollup._OrionAwsCostMetricsRollup__clamp_end_date('2026-09-01') == '2026-09-01'
        # requested end_date reaches into provisional days - clamped
        assert self.rollup._OrionAwsCostMetricsRollup__clamp_end_date('2026-10-01') == '2026-09-28'

    def test_upsert_document_updates_when_exists(self):
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = True
        doc = {'uuid': 'PSAP-2026-09-28', 'total_cost': 5}
        self.rollup._OrionAwsCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.update_elasticsearch_index.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', id='PSAP-2026-09-28', metadata=doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_not_called()

    def test_upsert_document_creates_when_missing(self):
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = False
        doc = {'uuid': 'PERFSCALE-2026-09-28', 'total_cost': 157}
        self.rollup._OrionAwsCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', data=doc, id='PERFSCALE-2026-09-28')

    def test_upsert_document_falls_back_to_create_on_error(self):
        self.mock_es_instance.verify_elastic_index_doc_id.side_effect = Exception('connection reset')
        doc = {'uuid': 'PERF-DEPT-2026-09-28', 'total_cost': 31}
        self.rollup._OrionAwsCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', data=doc, id='PERF-DEPT-2026-09-28')

    def test_destination_index_defaults_to_shared_cost_metrics_index(self):
        """Must default to the SAME index OrionCostMetricsRollup writes to (deliberate reuse)"""
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = False
        doc = {'uuid': 'PSAP-2026-09-28', 'total_cost': 5}
        self.rollup._OrionAwsCostMetricsRollup__upsert_document(doc)
        args, kwargs = self.mock_es_instance.upload_to_elasticsearch.call_args
        assert kwargs['index'] == 'cloud-governance-orion-cost-metrics-index'

    def test_destination_index_independently_overridable(self):
        """Override must use its own env var, not orion_cost_metrics_rollup's"""
        rollup = self._make_rollup({'orion_aws_cost_es_index': 'cloud-governance-orion-aws-cost-test-index'})
        mock_es = rollup._mock_es
        mock_es.verify_elastic_index_doc_id.return_value = False
        doc = {'uuid': 'PSAP-2026-09-28', 'total_cost': 5}
        rollup._OrionAwsCostMetricsRollup__upsert_document(doc)
        args, kwargs = mock_es.upload_to_elasticsearch.call_args
        assert kwargs['index'] == 'cloud-governance-orion-aws-cost-test-index'

    def test_run_without_es_configured(self):
        rollup = self._make_rollup({'es_host': ''})
        assert rollup.run() == {'status': 'no_upload', 'message': 'ES not configured'}

    @patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.OrionAwsCostMetricsRollup._OrionAwsCostMetricsRollup__today')
    def test_run_incremental_processes_trailing_window(self, mock_today):
        mock_today.return_value = datetime.date(2026, 10, 1)
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run()
        assert result['status'] == 'success'
        assert result['start_date'] == '2026-08-29'
        assert result['end_date'] == '2026-09-28'
        assert self.mock_es_instance.post_query.call_count == 1

    @patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.OrionAwsCostMetricsRollup._OrionAwsCostMetricsRollup__today')
    def test_run_backfill_entirely_inside_provisional_window_is_skipped_not_raised(self, mock_today):
        """A short recent backfill that clamps to before start_date must skip cleanly, not raise"""
        mock_today.return_value = datetime.date(2026, 10, 1)
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run(start_date='2026-09-30', end_date='2026-10-01')
        assert result['status'] == 'skipped'
        assert result['end_date'] == '2026-09-28'
        self.mock_es_instance.post_query.assert_not_called()

    def test_run_backfill_mode(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run(start_date='2024-01-01', end_date='2024-12-31')
        assert result['status'] == 'success'
        assert result['start_date'] == '2024-01-01'
        assert result['end_date'] == '2024-12-31'
        # Backfill chunks by month, so 12 months = 12 queries
        assert self.mock_es_instance.post_query.call_count == 12

    @patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.OrionAwsCostMetricsRollup._OrionAwsCostMetricsRollup__today')
    def test_run_backfill_clamps_end_date_to_avoid_provisional_days(self, mock_today):
        mock_today.return_value = datetime.date(2026, 10, 1)
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run(start_date='2026-09-01', end_date='2026-10-01')
        assert result['end_date'] == '2026-09-28'

    def test_run_partial_date_range_falls_back_to_incremental(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        with patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.logger') as mock_logger:
            result = self.rollup.run(start_date='2024-01-01')
        assert 'start_date' in result and 'end_date' in result
        # falling back to incremental means the returned range is the trailing
        # window, not the caller-supplied '2024-01-01'
        assert result['start_date'] != '2024-01-01'
        assert any('partial date range' in c.args[0].lower() for c in mock_logger.warning.call_args_list)

    def test_run_direct_start_with_configured_end_falls_back(self):
        """If caller provides start_date but only config has end_date, treat as partial and reject"""
        self.mock_es_instance.post_query.return_value = self._agg([])
        rollup = self._make_rollup({'orion_aws_cost_rollup_end_date': '2024-12-31'})
        with patch('cloud_governance.policy.common_policies.orion_aws_cost_metrics_rollup.logger') as mock_logger:
            result = rollup.run(start_date='2024-01-01')
        assert result['start_date'] != '2024-01-01'
        assert any('partial date range' in c.args[0].lower() for c in mock_logger.warning.call_args_list)

    def test_split_date_range_by_month_chunks_correctly(self):
        ranges = self.rollup._OrionAwsCostMetricsRollup__split_date_range_by_month('2024-01-01', '2024-03-31')
        assert len(ranges) == 3
        assert ranges[0] == ('2024-01-01', '2024-01-31')
        assert ranges[1] == ('2024-02-01', '2024-02-29')  # leap year
        assert ranges[2] == ('2024-03-01', '2024-03-31')

    def test_split_date_range_by_month_year_boundary(self):
        ranges = self.rollup._OrionAwsCostMetricsRollup__split_date_range_by_month('2024-11-15', '2025-02-28')
        assert len(ranges) == 4
        assert ranges[0] == ('2024-11-15', '2024-11-30')
        assert ranges[1] == ('2024-12-01', '2024-12-31')
        assert ranges[2] == ('2025-01-01', '2025-01-31')
        assert ranges[3] == ('2025-02-01', '2025-02-28')
