from unittest.mock import patch

from cloud_governance.policy.aws.optimize_resources_report import OptimizeResourcesReport


@patch('boto3.client')
def test_get_optimization_reports(mock_client):
    """
    This method tests the methods returns the data
    :return:
    :rtype:
    """
    optimize_reports = OptimizeResourcesReport()
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
                'resourcesFlagged': 123,
                'resourcesIgnored': 123,
                'resourcesSuppressed': 123
            },
            'flaggedResources': [
                {
                    'status': 'string',
                    'region': 'string',
                    'resourceId': 'string',
                    'isSuppressed': True,
                    'metadata': [
                        'test-123',
                    ]
                },
            ]
        }
    }
    response = optimize_reports.run()
    assert response == [{'ResourceId': 'test-123', 'ReportName': 'Test Report', 'Report': 'test_optimize_report'}]
