from cloud_governance.common.clouds.aws.athena.pyathena_operations import PyAthenaOperations
from tests.unittest.cloud_governance.common.clouds.aws.mocks.aws_mock import mock_athena


@mock_athena
def test_execute_query():
    """
    This method mock athena for the PyAthena
    :return:
    """
    athena_operations = PyAthenaOperations()
    expected_result = athena_operations.execute_query(query_string="select * from mock_table")
    actual_result = [{'A': 1, 'B': 0}, {'A': 2, 'B': 1}, {'A': 3, 'B': 2}]
    assert expected_result == actual_result
