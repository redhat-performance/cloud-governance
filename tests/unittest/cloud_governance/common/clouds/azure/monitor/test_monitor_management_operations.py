from azure.mgmt.monitor import MonitorManagementClient

from cloud_governance.common.clouds.azure.monitor.monitor_management_operations import MonitorManagementOperations
from tests.unittest.configs import AZURE_RESOURCE_ID
from tests.unittest.mocks.azure.mock_monitor.mock_monitor import mock_monitor


@mock_monitor
def test_monitor_management_operations__get_audit_records():
    """
    This method tests the get_start date
    :return:
    :rtype:
    """
    monitor_client = MonitorManagementClient(credential='', subscription_id='')
    monitor_client.activity_logs.create_log(
        caller='unittest@cloudgovernance.com',
        resource_id=AZURE_RESOURCE_ID
    )
    monitor_operations = MonitorManagementOperations()

    assert len(monitor_operations.get_audit_records(resource_id=AZURE_RESOURCE_ID)) == 1


