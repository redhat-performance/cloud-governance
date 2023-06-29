
from cloud_governance.common.clouds.azure.cost_management.cost_management_operations import CostManagementOperations


# def test_get_usage():
#     """
#     This method tests the azure usage results getting or not
#     @return:
#     """
#     cost_management_operations = CostManagementOperations()
#     cost_usage_data = cost_management_operations.get_usage(scope=cost_management_operations.azure_operations.scope)
#     assert cost_usage_data


def test_get_forecast():
    """
    This method tests the azure forecast results getting or not
    @return:
    """
    cost_management_operations = CostManagementOperations()
    cost_forecast_data = cost_management_operations.get_forecast(scope=cost_management_operations.azure_operations.scope)
    assert cost_forecast_data
