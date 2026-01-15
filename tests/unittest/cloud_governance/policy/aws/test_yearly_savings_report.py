from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from cloud_governance.policy.aws.yearly_savings_report import YearlySavingsReport
from tests.unittest.configs import ES_INDEX


class TestYearlySavingsReport:
    """Test suite for YearlySavingsReport class"""

    def setup_method(self):
        """Setup test fixtures"""
        with patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables') as mock_env_vars, \
             patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations') as mock_es_ops:
            mock_env_vars.environment_variables_dict = {
                'es_host': 'localhost',
                'es_port': '9200',
                'es_index': ES_INDEX,
                'account': 'TEST-ACCOUNT',
                'yearly_savings_es_index': 'cloud-governance-yearly-saving'
            }
            mock_es_instance = MagicMock()
            mock_es_ops.return_value = mock_es_instance
            self.report = YearlySavingsReport()

    def test_get_last_day_of_month(self):
        """Test __get_last_day_of_month method"""
        # Test February in non-leap year
        assert self.report._YearlySavingsReport__get_last_day_of_month(2023, 2) == 28

        # Test February in leap year
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 2) == 29

        # Test 30-day months
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 4) == 30
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 6) == 30
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 9) == 30
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 11) == 30

        # Test 31-day months
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 1) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 3) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 5) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 7) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 8) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 10) == 31
        assert self.report._YearlySavingsReport__get_last_day_of_month(2024, 12) == 31

    def test_split_date_range_by_month(self):
        """Test __split_date_range_by_month method"""
        # Test single month
        ranges = self.report._YearlySavingsReport__split_date_range_by_month('2026-01-01', '2026-01-31')
        assert len(ranges) == 1
        assert ranges[0] == ('2026-01-01', '2026-01-31')

        # Test two months
        ranges = self.report._YearlySavingsReport__split_date_range_by_month('2026-01-15', '2026-02-20')
        assert len(ranges) == 2
        assert ranges[0] == ('2026-01-15', '2026-01-31')
        assert ranges[1] == ('2026-02-01', '2026-02-20')

        # Test cross-year
        ranges = self.report._YearlySavingsReport__split_date_range_by_month('2026-12-15', '2027-01-10')
        assert len(ranges) == 2
        assert ranges[0] == ('2026-12-15', '2026-12-31')
        assert ranges[1] == ('2027-01-01', '2027-01-10')

        # Test full year
        ranges = self.report._YearlySavingsReport__split_date_range_by_month('2026-01-01', '2026-12-31')
        assert len(ranges) == 12

        # Test invalid date range
        try:
            self.report._YearlySavingsReport__split_date_range_by_month('2026-01-15', '2026-01-10')
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "start_date" in str(e) or "must be <=" in str(e)

        # Test missing dates
        try:
            self.report._YearlySavingsReport__split_date_range_by_month('', '2026-01-10')
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "must be provided" in str(e)

    def test_get_total_policy_sum(self):
        """Test __get_total_policy_sum method"""
        all_resources = {
            'resource-1': {'policy_name': 'unused_nat_gateway', 'savings': 100.5},
            'resource-2': {'policy_name': 'unused_nat_gateway', 'savings': 200.3},
            'resource-3': {'policy_name': 'ip_unattached', 'savings': 50.2},
            'resource-4': {'policy_name': 'ip_unattached', 'savings': 75.8},
            'resource-5': {'policy_name': 'zombie_snapshots', 'savings': 300.0}
        }

        result = self.report._YearlySavingsReport__get_total_policy_sum(all_resources)

        assert result['unused_nat_gateway'] == 300.8
        assert result['ip_unattached'] == 126.0
        assert result['zombie_snapshots'] == 300.0

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_process_monthly_query(self, mock_env_vars, mock_es_ops):
        """Test __process_monthly_query method"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.post_query.return_value = {
            'PolicyName': {
                'buckets': [
                    {
                        'key': 'unused_nat_gateway',
                        'CapturedDate': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-01-10T00:00:00.000Z',
                                    'ResourceId': {
                                        'buckets': [
                                            {
                                                'key': 'nat-123',
                                                'Savings': {'value': 381.24}
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                    {
                        'key': 'ip_unattached',
                        'CapturedDate': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-01-12T00:00:00.000Z',
                                    'ResourceId': {
                                        'buckets': [
                                            {
                                                'key': 'eip-456',
                                                'Savings': {'value': 42.36}
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report._YearlySavingsReport__process_monthly_query('2026-01-01', '2026-01-31')

        assert len(result) == 2
        assert 'nat-123' in result
        assert 'eip-456' in result
        assert result['nat-123']['policy_name'] == 'unused_nat_gateway'
        assert result['nat-123']['savings'] == 381.24
        assert result['eip-456']['policy_name'] == 'ip_unattached'
        assert result['eip-456']['savings'] == 42.36

    @patch('cloud_governance.policy.aws.yearly_savings_report.datetime')
    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_process_monthly_query_with_zero_savings(self, mock_env_vars, mock_es_ops, mock_datetime):
        """Test __process_monthly_query when savings is 0 (uses fallback)"""
        fixed_now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime = datetime.strptime
        mock_datetime.timezone = timezone

        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.post_query.return_value = {
            'PolicyName': {
                'buckets': [
                    {
                        'key': 'unused_nat_gateway',
                        'CapturedDate': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-01-10T00:00:00.000Z',
                                    'ResourceId': {
                                        'buckets': [
                                            {
                                                'key': 'nat-123',
                                                'Savings': {'value': 0}  # Zero savings
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report._YearlySavingsReport__process_monthly_query('2026-01-01', '2026-01-31')

        assert 'nat-123' in result
        expected_savings = 355 * 24 * 0.045
        assert abs(result['nat-123']['savings'] - expected_savings) < 0.01

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_get_yearly_savings(self, mock_env_vars, mock_es_ops):
        """Test __get_yearly_savings method"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        # Mock response for January
        mock_es_instance.post_query.return_value = {
            'PolicyName': {
                'buckets': [
                    {
                        'key': 'unused_nat_gateway',
                        'CapturedDate': {
                            'buckets': [
                                {
                                    'key_as_string': '2026-01-10T00:00:00.000Z',
                                    'ResourceId': {
                                        'buckets': [
                                            {
                                                'key': 'nat-123',
                                                'Savings': {'value': 381.24}
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report._YearlySavingsReport__get_yearly_savings('2026-01-01', '2026-01-31')

        assert 'unused_nat_gateway' in result
        assert result['unused_nat_gateway'] > 0

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_update_yearly_savings(self, mock_env_vars, mock_es_ops):
        """Test __update_yearly_savings method"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.verify_elastic_index_doc_id.return_value = False  # Document doesn't exist
        mock_es_instance.upload_to_elasticsearch.return_value = True
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        all_months_data = {1: 100.5, 2: 200.3, 3: 150.0}
        total_annual_saving = 450.8

        result = report._YearlySavingsReport__update_yearly_savings(2026, all_months_data, total_annual_saving)

        assert result is True
        mock_es_instance.upload_to_elasticsearch.assert_called_once()
        call_args = mock_es_instance.upload_to_elasticsearch.call_args
        assert call_args[1]['index'] == 'cloud-governance-yearly-saving'
        assert call_args[1]['id'] == '2026-TEST-ACCOUNT'
        assert call_args[1]['data']['year'] == 2026
        assert call_args[1]['data']['total_saving'] == 450.8
        assert call_args[1]['data']['account'] == 'TEST-ACCOUNT'
        assert call_args[1]['data']['month_1'] == 100.5
        assert call_args[1]['data']['month_2'] == 200.3
        assert call_args[1]['data']['month_3'] == 150.0

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_update_yearly_savings_update_existing(self, mock_env_vars, mock_es_ops):
        """Test __update_yearly_savings when document exists (update)"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.verify_elastic_index_doc_id.return_value = True
        mock_es_instance.update_elasticsearch_index.return_value = True
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        all_months_data = {1: 100.5}
        total_annual_saving = 100.5

        result = report._YearlySavingsReport__update_yearly_savings(2026, all_months_data, total_annual_saving)

        assert result is True
        mock_es_instance.update_elasticsearch_index.assert_called_once()
        mock_es_instance.upload_to_elasticsearch.assert_not_called()

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    @patch('cloud_governance.policy.aws.yearly_savings_report.time.sleep')
    def test_run_with_custom_dates(self, mock_sleep, mock_env_vars, mock_es_ops):
        """Test run method with custom date range"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.post_query.return_value = {
            'PolicyName': {'buckets': []}
        }
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report.run(start_date='2026-01-01', end_date='2026-01-07')

        assert result['status'] == 'success'
        assert result['custom_date_range'] is True
        assert result['start_date'] == '2026-01-01'
        assert result['end_date'] == '2026-01-07'
        assert 'policy_savings' in result
        assert 'total_yearly_savings' in result

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    @patch('cloud_governance.policy.aws.yearly_savings_report.time.sleep')
    def test_run_default_current_year(self, mock_sleep, mock_env_vars, mock_es_ops):
        """Test run method with default current year"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.post_query.return_value = {
            'PolicyName': {'buckets': []}
        }
        mock_es_instance.verify_elastic_index_doc_id.return_value = False
        mock_es_instance.upload_to_elasticsearch.return_value = True
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report.run()

        assert result['status'] == 'success'
        assert 'year' in result
        assert 'total_yearly_savings' in result
        assert 'monthly_savings' in result
        assert result['year'] == datetime.now(timezone.utc).year

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_run_no_es_configured(self, mock_env_vars, mock_es_ops):
        """Test run method when ES is not configured"""
        mock_env_vars.environment_variables_dict = {
            'es_host': '',
            'es_port': '',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT'
        }

        mock_es_ops.return_value = None

        report = YearlySavingsReport()
        result = report.run()

        assert result['status'] == 'no_upload'
        assert 'ES not configured' in result['message']

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_calculate_month_savings(self, mock_env_vars, mock_es_ops):
        """Test __calculate_month_savings method"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_instance.post_query.return_value = {
            'PolicyName': {'buckets': []}
        }
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        result = report._YearlySavingsReport__calculate_month_savings(2026, 1, 1, 31)

        assert isinstance(result, dict)

    @patch('cloud_governance.policy.aws.yearly_savings_report.ElasticSearchOperations')
    @patch('cloud_governance.policy.aws.yearly_savings_report.environment_variables')
    def test_account_normalization(self, mock_env_vars, mock_es_ops):
        """Test account name normalization"""
        mock_env_vars.environment_variables_dict = {
            'es_host': 'localhost',
            'es_port': '9200',
            'es_index': ES_INDEX,
            'account': 'OPENSHIFT-TEST-ACCOUNT',
            'yearly_savings_es_index': 'cloud-governance-yearly-saving'
        }

        mock_es_instance = MagicMock()
        mock_es_ops.return_value = mock_es_instance

        report = YearlySavingsReport()
        assert report._YearlySavingsReport__account == 'TEST-ACCOUNT'

        del mock_env_vars.environment_variables_dict['account']
        report2 = YearlySavingsReport()
        assert report2._YearlySavingsReport__account == 'PERF-DEPT'
