"""
Integration test for yearly_savings_report policy
Tests uploading policy data, running the report, and verifying results in Elasticsearch
"""
import os
import time
from datetime import datetime, timezone, date

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.policy.aws.yearly_savings_report import YearlySavingsReport
from cloud_governance.main.environment_variables import environment_variables
from tests.integration.test_environment_variables import test_environment_variable

es_host = test_environment_variable.get('elasticsearch', 'localhost')
es_port = test_environment_variable.get('elasticsearch_port', '9200')

policy_index = 'test-cloud-governance-policy-es-index'
yearly_savings_index = 'test-cloud-governance-yearly-saving'

test_account = 'TEST-ACCOUNT'


def setup_test_data(es_ops: ElasticSearchOperations):
    """
    Upload sample policy data to Elasticsearch for testing
    """
    try:
        es_ops.delete_data_in_es(es_index=policy_index)
        es_ops.delete_data_in_es(es_index=yearly_savings_index)
    except Exception:
            pass
    time.sleep(2)

    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    current_day = now.day

    test_date_1 = date(current_year, current_month, 1)
    test_date_2 = date(current_year, current_month, min(5, current_day))

    test_policies = [
        {
            'PublicCloud': 'AWS',
            'account': test_account,
            'policy': 'unused_nat_gateway',
            'timestamp': test_date_1.isoformat(),
            'ResourceId': 'nat-gateway-001',
            'TotalYearlySavings': 100.50,
            'RegionName': 'us-east-1'
        },
        {
            'PublicCloud': 'AWS',
            'account': test_account,
            'policy': 'unused_nat_gateway',
            'timestamp': test_date_2.isoformat(),
            'ResourceId': 'nat-gateway-001',
            'TotalYearlySavings': 150.75,
            'RegionName': 'us-east-1'
        },
        {
            'PublicCloud': 'AWS',
            'account': test_account,
            'policy': 'ip_unattached',
            'timestamp': test_date_1.isoformat(),
            'ResourceId': 'eip-allocation-001',
            'TotalYearlySavings': 50.25,
            'RegionName': 'us-east-1'
        },
        {
            'PublicCloud': 'AWS',
            'account': test_account,
            'policy': 'zombie_snapshots',
            'timestamp': test_date_2.isoformat(),
            'ResourceId': 'snap-1234567890',
            'TotalYearlySavings': 200.00,
            'RegionName': 'us-east-1'
        },
        {
            'PublicCloud': 'AWS',
            'account': test_account,
            'policy': 'unattached_volume',
            'timestamp': test_date_1.isoformat(),
            'ResourceId': 'vol-1234567890',
            'TotalYearlySavings': 75.30,
            'RegionName': 'us-east-1'
        }
    ]

    for policy_data in test_policies:
        es_ops.upload_to_elasticsearch(index=policy_index, data=policy_data)

    time.sleep(3)

    return len(test_policies)


def wait_for_document(es_ops: ElasticSearchOperations, index: str, doc_id: str, max_retries: int = 10, delay: float = 1.0):
    """
    Wait for a document to appear in Elasticsearch with retry logic
    """
    for attempt in range(max_retries):
        try:
            if es_ops.verify_elastic_index_doc_id(index=index, doc_id=doc_id):
                return es_ops.get_elasticsearch_index_by_id(index=index, id=doc_id)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            else:
                raise Exception(f"Document {doc_id} not found in index {index} after {max_retries} attempts: {e}")
    raise Exception(f"Document {doc_id} not found in index {index} after {max_retries} attempts")


def test_yearly_savings_report_integration():
    """
    Integration test for yearly_savings_report:
    1. Upload sample policy data to ES (using current month dates)
    2. Run yearly_savings_report (without custom dates to trigger ES upload)
    3. Verify data was uploaded to yearly savings index
    4. Fetch and verify the data structure
    """
    if not es_host:
        return

    es_ops = ElasticSearchOperations(es_host=es_host, es_port=es_port)

    if not es_ops.check_elastic_search_connection():
        raise Exception(f"Could not connect to Elasticsearch at {es_host}:{es_port}")

    try:
        # Step 1: Setup test data
        num_policies = setup_test_data(es_ops)
        assert num_policies > 0, "Failed to setup test data"

        # Step 2: Run yearly_savings_report
        current_year = datetime.now(timezone.utc).year
        current_month = datetime.now(timezone.utc).month

        environment_variables.environment_variables_dict['es_host'] = es_host
        environment_variables.environment_variables_dict['es_port'] = str(es_port)
        environment_variables.environment_variables_dict['es_index'] = policy_index
        environment_variables.environment_variables_dict['account'] = test_account
        environment_variables.environment_variables_dict['yearly_savings_es_index'] = yearly_savings_index
        environment_variables.environment_variables_dict['yearly_savings_start_date'] = ''
        environment_variables.environment_variables_dict['yearly_savings_end_date'] = ''

        os.environ['es_host'] = es_host
        os.environ['es_port'] = str(es_port)
        os.environ['es_index'] = policy_index
        os.environ['account'] = test_account
        os.environ['yearly_savings_es_index'] = yearly_savings_index
        os.environ.pop('yearly_savings_start_date', None)
        os.environ.pop('yearly_savings_end_date', None)

        report = YearlySavingsReport()
        result = report.run()

        assert result['status'] == 'success', f"Report failed: {result.get('message', 'Unknown error')}"
        assert 'year' in result, "Result should contain year"
        assert 'total_yearly_savings' in result, "Result should contain total_yearly_savings"
        assert 'monthly_savings' in result, "Result should contain monthly_savings (not policy_savings for default behavior)"
        assert result['year'] == current_year, f"Year mismatch: expected {current_year}, got {result['year']}"

        # Step 3: Verify data was uploaded to yearly savings index with retry logic
        year_id = f"{current_year}-{test_account}"

        yearly_doc = wait_for_document(es_ops, yearly_savings_index, year_id, max_retries=10, delay=1.0)

        assert yearly_doc is not None, f"Yearly savings document {year_id} not found"
        assert '_source' in yearly_doc, "Document should have _source"

        source = yearly_doc['_source']

        # Step 4: Verify the data structure
        assert source['year'] == current_year, f"Year mismatch: expected {current_year}, got {source['year']}"
        assert source['account'] == test_account, f"Account mismatch: expected {test_account}, got {source['account']}"
        assert 'total_saving' in source, "Document should have total_saving"
        assert source['total_saving'] >= 0, f"Total saving should be >= 0, got {source['total_saving']}"
        assert 'policy' in source, "Document should have policy field"
        assert source['policy'] == 'yearly_savings_report', f"Policy should be 'yearly_savings_report', got {source['policy']}"

        for month in range(1, 13):
            assert f'month_{month}' in source, f"Document should have month_{month} field"

        current_month_savings = source[f'month_{current_month}']
        assert current_month_savings >= 0, f"Current month ({current_month}) should have savings >= 0, got {current_month_savings}"

        assert 'timestamp' in source, "Document should have timestamp"
        assert 'last_updated' in source, "Document should have last_updated"

        assert abs(source['total_saving'] - result['total_yearly_savings']) < 0.01, \
            f"Total saving mismatch: ES has {source['total_saving']}, result has {result['total_yearly_savings']}"

        print(f"✅ Integration test passed!")
        print(f"   Year: {source['year']}")
        print(f"   Account: {source['account']}")
        print(f"   Total Savings: ${source['total_saving']:.2f}")
        print(f"   Current Month ({current_month}) Savings: ${current_month_savings:.2f}")
        print(f"   Monthly Savings: {result['monthly_savings']}")

    finally:
        try:
            es_ops.delete_data_in_es(es_index=policy_index)
            es_ops.delete_data_in_es(es_index=yearly_savings_index)
        except Exception as e:
            print(f"Warning: Failed to cleanup test data: {e}")
