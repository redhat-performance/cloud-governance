
from functools import wraps
from unittest.mock import patch

from azure.mgmt.monitor import MonitorManagementClient

from tests.unittest.mocks.azure.mock_monitor.mock_activity_logs_operations import MockActivityLogsOperations
from tests.unittest.mocks.azure.mock_monitor.mock_metric_operations import MockMetricOperations


def mock_monitor(method):
    """
    This method is mocking for Jira class methods which are used in Jira Operations    @param method:
    @return:
    """

    @wraps(method)
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        with patch.object(MonitorManagementClient, 'activity_logs', MockActivityLogsOperations()), \
                patch.object(MonitorManagementClient, 'metrics', MockMetricOperations()):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
