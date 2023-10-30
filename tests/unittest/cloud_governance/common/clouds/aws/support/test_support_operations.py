from unittest.mock import patch

from cloud_governance.common.clouds.aws.support.support_operations import SupportOperations


@patch('boto3.client')
def test_get_describe_trusted_advisor_checks(mock_client):
    """
    This method tests the get_describe_trusted_advisor_checks method
    :param mock_client:
    :type mock_client:
    :return:
    :rtype:
    """
    mock_client.return_value.describe_trusted_advisor_checks.return_value = {
        'checks': [
            {
                'id': 'test_report',
                'name': 'Test Report',
                'category': 'test_optimize_report',
                'metadata': [
                    'ResourceId',
                ]
            },
        ]
    }
    support_operations = SupportOperations()
    response = support_operations.get_describe_trusted_advisor_checks()
    assert response == [{'id': 'test_report', 'name': 'Test Report', 'category': 'test_optimize_report', 'metadata': ['ResourceId']}]


@patch('boto3.client')
def test_get_trusted_advisor_reports(mock_client):
    """
    This method tests the get_trusted_advisor_reports method
    :param mock_client:
    :type mock_client:
    :return:
    :rtype:
    """
    mock_client.return_value.describe_trusted_advisor_checks.return_value = {
        'checks': [
            {
                'id': 'test_report',
                'name': 'Test Report',
                'category': 'test_optimize_report',
                'metadata': [
                    'ResourceId',
                ]
            },
        ]
    }
    mock_client.return_value.describe_trusted_advisor_check_result.return_value = {
        'result': {
            'checkId': 'test_report',
            'resourcesSummary': {
                'resourcesProcessed': 123,
            },
            'flaggedResources': [
                {
                    'metadata': [
                        'test-123',
                    ]
                },
            ]
        }
    }
    support_operations = SupportOperations()
    response = support_operations.get_trusted_advisor_reports()
    assert response == {'test_optimize_report': {'test_report': {'metadata': {'id': 'test_report', 'name': 'Test Report', 'category': 'test_optimize_report', 'metadata': ['ResourceId']}, 'reports': {'checkId': 'test_report', 'resourcesSummary': {'resourcesProcessed': 123}, 'flaggedResources': [{'metadata': ['test-123']}]}}}}
