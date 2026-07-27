from unittest.mock import patch, MagicMock

from cloud_governance.policy.aws.orion_metrics_rollup import OrionMetricsRollup
from tests.unittest.configs import ES_INDEX


class TestOrionMetricsRollup:
    """Test suite for OrionMetricsRollup class"""

    def setup_method(self):
        """Setup test fixtures"""
        with patch('cloud_governance.policy.aws.orion_metrics_rollup.environment_variables') as mock_env_vars, \
             patch('cloud_governance.policy.aws.orion_metrics_rollup.ElasticSearchOperations') as mock_es_ops:
            mock_env_vars.environment_variables_dict = {
                'es_host': 'localhost',
                'es_port': '9200',
                'es_index': ES_INDEX,
                'account': 'TEST-ACCOUNT',
                'orion_metrics_es_index': 'cloud-governance-orion-metrics-index'
            }
            mock_es_instance = MagicMock()
            mock_es_ops.return_value = mock_es_instance
            self.rollup = OrionMetricsRollup()
            self.mock_es_instance = mock_es_instance

    def test_split_date_range_by_month(self):
        """Test __split_date_range_by_month method"""
        ranges = self.rollup._OrionMetricsRollup__split_date_range_by_month('2026-01-01', '2026-01-31')
        assert len(ranges) == 1
        assert ranges[0] == ('2026-01-01', '2026-01-31')

        ranges = self.rollup._OrionMetricsRollup__split_date_range_by_month('2026-01-15', '2026-02-20')
        assert len(ranges) == 2
        assert ranges[0] == ('2026-01-15', '2026-01-31')
        assert ranges[1] == ('2026-02-01', '2026-02-20')

        try:
            self.rollup._OrionMetricsRollup__split_date_range_by_month('2026-01-15', '2026-01-10')
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "must be <=" in str(e)

        try:
            self.rollup._OrionMetricsRollup__split_date_range_by_month('', '2026-01-10')
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "must be provided" in str(e)

    def test_parse_response_fills_all_tracked_policies(self):
        """A day with only some policies present should still get a 0 count for the others"""
        response = {
            'by_account': {
                'buckets': [
                    {
                        'key': 'my-account',
                        'by_day': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-07-04T00:00:00.000Z',
                                    'by_policy': {
                                        'buckets': [
                                            {'key': 'zombie_cluster_resource', 'doc_count': 25},
                                            {'key': 'ec2_stop', 'doc_count': 3}
                                        ]
                                    },
                                    'total_savings': {'value': 1234.6}
                                }
                            ]
                        }
                    }
                ]
            }
        }

        documents = self.rollup._OrionMetricsRollup__parse_response(response)

        assert len(documents) == 1
        doc = documents[0]
        assert doc['uuid'] == 'my-account-2026-07-04'
        assert doc['timestamp'] == '2026-07-04T00:00:00Z'
        assert doc['account'] == 'my-account'
        assert doc['zombie_cluster_resource_count'] == 25
        assert doc['ec2_stop_count'] == 3
        # untouched tracked policies default to 0, not missing
        assert doc['s3_inactive_count'] == 0
        assert doc['unused_access_key_count'] == 0
        assert doc['delete_access_key_count'] == 0
        # rounded to a whole number, not a float
        assert doc['monitored_policies_savings'] == 1235
        assert isinstance(doc['monitored_policies_savings'], int)

    def test_parse_response_empty_day_defaults_to_zero(self):
        """A day bucket with no matching policy docs should produce an all-zero document, not be skipped"""
        response = {
            'by_account': {
                'buckets': [
                    {
                        'key': 'quiet-account',
                        'by_day': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-07-05T00:00:00.000Z',
                                    'by_policy': {'buckets': []},
                                    'total_savings': {'value': 0}
                                }
                            ]
                        }
                    }
                ]
            }
        }

        documents = self.rollup._OrionMetricsRollup__parse_response(response)

        assert len(documents) == 1
        doc = documents[0]
        for policy in OrionMetricsRollup.TRACKED_POLICIES:
            assert doc[f'{policy}_count'] == 0
        assert doc['monitored_policies_savings'] == 0

    def test_parse_response_handles_missing_aggregations(self):
        """An unexpected/empty response should produce no documents, not raise"""
        assert self.rollup._OrionMetricsRollup__parse_response({}) == []
        assert self.rollup._OrionMetricsRollup__parse_response(None) == []

    def test_upsert_document_updates_when_doc_exists(self):
        """If the doc id already exists, update it instead of creating a new one"""
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = True
        document = {'uuid': 'my-account-2026-07-04', 'zombie_cluster_resource_count': 5}

        self.rollup._OrionMetricsRollup__upsert_document(document)

        self.mock_es_instance.update_elasticsearch_index.assert_called_once_with(
            index='cloud-governance-orion-metrics-index',
            id='my-account-2026-07-04',
            metadata=document
        )
        self.mock_es_instance.upload_to_elasticsearch.assert_not_called()

    def test_upsert_document_creates_when_doc_missing(self):
        """If the doc id doesn't exist yet, create it"""
        self.mock_es_instance.verify_elastic_index_doc_id.return_value = False
        document = {'uuid': 'my-account-2026-07-05', 'zombie_cluster_resource_count': 0}

        self.rollup._OrionMetricsRollup__upsert_document(document)

        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-metrics-index',
            data=document,
            id='my-account-2026-07-05'
        )
        self.mock_es_instance.update_elasticsearch_index.assert_not_called()

    def test_upsert_document_falls_back_to_create_on_update_error(self):
        """If checking/updating an existing doc errors out, fall back to create rather than losing the data"""
        self.mock_es_instance.verify_elastic_index_doc_id.side_effect = Exception('connection reset')
        document = {'uuid': 'my-account-2026-07-06', 'zombie_cluster_resource_count': 1}

        self.rollup._OrionMetricsRollup__upsert_document(document)

        self.mock_es_instance.upload_to_elasticsearch.assert_called_once_with(
            index='cloud-governance-orion-metrics-index',
            data=document,
            id='my-account-2026-07-06'
        )

    def test_run_without_es_configured(self):
        """run() should no-op cleanly when ES isn't configured, not raise"""
        with patch('cloud_governance.policy.aws.orion_metrics_rollup.environment_variables') as mock_env_vars:
            mock_env_vars.environment_variables_dict = {'es_host': '', 'es_port': ''}
            rollup = OrionMetricsRollup()
            result = rollup.run()
            assert result == {'status': 'no_upload', 'message': 'ES not configured'}

    def test_run_daily_mode_defaults_to_today(self):
        """With no start/end date given, run() should roll up a single day (today), not backfill"""
        self.mock_es_instance.post_query.return_value = {'by_account': {'buckets': []}}

        result = self.rollup.run()

        assert result['status'] == 'success'
        assert result['documents_written'] == 0
        assert 'date' in result
        assert self.mock_es_instance.post_query.call_count == 1

    def test_run_backfill_mode_chunks_by_month(self):
        """With an explicit date range spanning two months, run() should query once per month"""
        self.mock_es_instance.post_query.return_value = {'by_account': {'buckets': []}}

        result = self.rollup.run(start_date='2026-01-15', end_date='2026-02-10')

        assert result['status'] == 'success'
        assert self.mock_es_instance.post_query.call_count == 2

    def test_build_query_filters_to_tracked_policies_only(self):
        """The source query must scope to the tracked policies, not every policy in the index"""
        query = self.rollup._OrionMetricsRollup__build_query('2026-07-01', '2026-07-31')

        policy_filter = query['query']['bool']['filter'][1]['terms']['policy.keyword']
        assert set(policy_filter) == set(OrionMetricsRollup.TRACKED_POLICIES)
