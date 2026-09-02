from unittest.mock import patch, MagicMock

from cloud_governance.policy.common_policies.orion_cost_metrics_rollup import OrionCostMetricsRollup


class TestOrionCostMetricsRollup:
    """Test suite for OrionCostMetricsRollup class"""

    def _make_rollup(self, env_overrides=None):
        base_env = {
            'es_host': 'localhost',
            'es_port': '9200',
            'orion_cost_es_index': 'cloud-governance-orion-cost-metrics-index',
            'orion_cost_center': '999',  # generic test cost center (not internal)
        }
        if env_overrides:
            base_env.update(env_overrides)
        with patch('cloud_governance.policy.common_policies.orion_cost_metrics_rollup.environment_variables') as mock_env, \
             patch('cloud_governance.policy.common_policies.orion_cost_metrics_rollup.ElasticSearchOperations') as mock_es_ops:
            mock_env.environment_variables_dict = base_env
            mock_es_instance = MagicMock()
            mock_es_ops.return_value = mock_es_instance
            rollup = OrionCostMetricsRollup()
            rollup._mock_es = mock_es_instance
            return rollup

    def setup_method(self):
        self.rollup = self._make_rollup()
        self.mock_es_instance = self.rollup._mock_es

    def _agg(self, buckets):
        return {'by_month': {'buckets': buckets}}

    def test_build_query_filters_cost_center_policies_and_actual(self):
        """Query must scope to the configured cost center, spend policies, and Actual>0"""
        query = self.rollup._OrionCostMetricsRollup__build_query('2026-01-01', '2026-07-31')
        filters = query['query']['bool']['filter']

        cc = [f for f in filters if 'term' in f and 'CostCenter' in f.get('term', {})]
        assert cc and cc[0]['term']['CostCenter'] == 999

        pol = [f for f in filters if 'terms' in f and 'policy.keyword' in f.get('terms', {})]
        assert set(pol[0]['terms']['policy.keyword']) == set(OrionCostMetricsRollup.SPEND_POLICIES)

        actual = [f for f in filters if 'range' in f and 'Actual' in f.get('range', {})]
        assert actual and actual[0]['range']['Actual'] == {'gt': 0}

        # monthly buckets
        assert query['aggs']['by_month']['date_histogram']['calendar_interval'] == 'month'

    @patch('cloud_governance.policy.common_policies.orion_cost_metrics_rollup.OrionCostMetricsRollup._OrionCostMetricsRollup__first_of_current_month')
    def test_parse_response_builds_per_month_doc_with_cloud_split(self, mock_first):
        """A completed month maps clouds to fields, fills missing clouds with 0, rounds to int"""
        import datetime
        mock_first.return_value = datetime.date(2026, 9, 1)  # current month = 2026-09

        response = self._agg([
            {
                'key_as_string': '2026-07-01',
                'by_cloud': {'buckets': [
                    {'key': 'AWS', 'spend': {'value': 17512.4}},
                    {'key': 'AZURE', 'spend': {'value': 14780.6}},
                    {'key': 'IBM Cloud', 'spend': {'value': 191536.0}},
                ]},
                'total': {'value': 223829.0}
            }
        ])
        docs = self.rollup._OrionCostMetricsRollup__parse_response(response)

        assert len(docs) == 1
        doc = docs[0]
        assert doc['uuid'] == 'CC999-2026-07'
        assert doc['account'] == 'CC999'
        assert doc['timestamp'] == '2026-07-01T00:00:00Z'
        assert doc['aws_cost'] == 17512
        assert doc['azure_cost'] == 14781
        assert doc['ibm_cost'] == 191536
        assert doc['gcp_cost'] == 0  # missing cloud defaults to 0
        assert doc['total_cost'] == 223829
        assert all(isinstance(doc[f], int) for f in ['total_cost', 'aws_cost', 'azure_cost', 'gcp_cost', 'ibm_cost'])

    @patch('cloud_governance.policy.common_policies.orion_cost_metrics_rollup.OrionCostMetricsRollup._OrionCostMetricsRollup__first_of_current_month')
    def test_parse_response_skips_in_progress_and_future_months(self, mock_first):
        """The current (in-progress) month and any future months must be excluded"""
        import datetime
        mock_first.return_value = datetime.date(2026, 9, 1)

        response = self._agg([
            {'key_as_string': '2026-08-01', 'by_cloud': {'buckets': [{'key': 'AWS', 'spend': {'value': 100}}]}, 'total': {'value': 100}},
            {'key_as_string': '2026-09-01', 'by_cloud': {'buckets': [{'key': 'AWS', 'spend': {'value': 5}}]}, 'total': {'value': 5}},   # in-progress
            {'key_as_string': '2026-10-01', 'by_cloud': {'buckets': [{'key': 'AWS', 'spend': {'value': 0}}]}, 'total': {'value': 0}},   # future
        ])
        docs = self.rollup._OrionCostMetricsRollup__parse_response(response)

        assert len(docs) == 1
        assert docs[0]['uuid'] == 'CC999-2026-08'

    def test_parse_response_folds_awscloud_into_aws(self):
        """The legacy AWSCLOUD label must be folded into aws_cost, not dropped"""
        with patch.object(OrionCostMetricsRollup, '_OrionCostMetricsRollup__first_of_current_month', return_value=__import__('datetime').date(2026, 9, 1)):
            response = self._agg([
                {'key_as_string': '2026-05-01', 'by_cloud': {'buckets': [
                    {'key': 'AWS', 'spend': {'value': 10}},
                    {'key': 'AWSCLOUD', 'spend': {'value': 5}},
                ]}, 'total': {'value': 15}}
            ])
            docs = self.rollup._OrionCostMetricsRollup__parse_response(response)
        assert docs[0]['aws_cost'] == 15

    def test_parse_response_handles_missing_aggregations(self):
        assert self.rollup._OrionCostMetricsRollup__parse_response({}) == []
        assert self.rollup._OrionCostMetricsRollup__parse_response(None) == []

    def test_upsert_document_updates_when_exists(self):
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = True
        doc = {'uuid': 'CC999-2026-07', 'total_cost': 100}
        self.rollup._OrionCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.update_elasticsearch_index.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', id='CC999-2026-07', metadata=doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_not_called()

    def test_upsert_document_creates_when_missing(self):
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = False
        doc = {'uuid': 'CC999-2026-08', 'total_cost': 0}
        self.rollup._OrionCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', data=doc, id='CC999-2026-08')

    def test_upsert_document_falls_back_to_create_on_error(self):
        self.mock_es_instance.verify_elastic_index_doc_id.side_effect = Exception('connection reset')
        doc = {'uuid': 'CC999-2026-06', 'total_cost': 1}
        self.rollup._OrionCostMetricsRollup__upsert_document(doc)
        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-cost-metrics-index', data=doc, id='CC999-2026-06')

    def test_run_without_es_configured(self):
        rollup = self._make_rollup({'es_host': ''})
        assert rollup.run() == {'status': 'no_upload', 'message': 'ES not configured'}

    def test_run_skips_when_cost_center_unset(self):
        """No cost center configured -> skip cleanly (no internal number hardcoded)"""
        rollup = self._make_rollup({'orion_cost_center': ''})
        result = rollup.run()
        assert result['status'] == 'skipped'
        assert 'orion_cost_center' in result['message']
        rollup._mock_es.post_query.assert_not_called()

    def test_run_incremental_processes_last_completed_month(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run()
        assert result['status'] == 'success'
        assert 'month' in result
        assert self.mock_es_instance.post_query.call_count == 1

    def test_run_backfill_mode(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run(start_date='2024-01-01', end_date='2024-12-31')
        assert result['status'] == 'success'
        assert result['start_date'] == '2024-01-01'
        assert result['end_date'] == '2024-12-31'
        # Backfill chunks by month, so 12 months = 12 queries
        assert self.mock_es_instance.post_query.call_count == 12

    def test_run_partial_date_range_falls_back_to_incremental(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        with patch('cloud_governance.policy.common_policies.orion_cost_metrics_rollup.logger') as mock_logger:
            result = self.rollup.run(start_date='2024-01-01')
        assert 'month' in result
        assert 'start_date' not in result
        assert any('partial date range' in c.args[0].lower() for c in mock_logger.warning.call_args_list)

    def test_split_date_range_by_month_chunks_correctly(self):
        ranges = self.rollup._OrionCostMetricsRollup__split_date_range_by_month('2024-01-01', '2024-03-31')
        assert len(ranges) == 3
        assert ranges[0] == ('2024-01-01', '2024-01-31')
        assert ranges[1] == ('2024-02-01', '2024-02-29')  # leap year
        assert ranges[2] == ('2024-03-01', '2024-03-31')

    def test_split_date_range_by_month_year_boundary(self):
        ranges = self.rollup._OrionCostMetricsRollup__split_date_range_by_month('2024-11-15', '2025-02-28')
        assert len(ranges) == 4
        assert ranges[0] == ('2024-11-15', '2024-11-30')
        assert ranges[1] == ('2024-12-01', '2024-12-31')
        assert ranges[2] == ('2025-01-01', '2025-01-31')
        assert ranges[3] == ('2025-02-01', '2025-02-28')

    def test_run_backfill_chunks_by_month(self):
        self.mock_es_instance.post_query.return_value = self._agg([])
        result = self.rollup.run(start_date='2024-01-01', end_date='2024-03-31')
        assert result['status'] == 'success'
        # post_query called once per month (3 months)
        assert self.mock_es_instance.post_query.call_count == 3
