
from cloud_governance.common.clouds.azure.cost_management.cost_management_operations import CostManagementOperations


def test_get_usage():
    """
    This method tests the azure usage results getting or not
    @return:
    """
    cost_management_operations = CostManagementOperations()
    cost_usage_data = cost_management_operations.get_usage()
    assert cost_usage_data.get('rows')


def test_get_forecast():
    """
    This method tests the azure forecast results getting or not
    @return:
    """
    cost_management_operations = CostManagementOperations()
    cost_forecast_data = cost_management_operations.get_forecast()
    assert cost_forecast_data.get('rows')
