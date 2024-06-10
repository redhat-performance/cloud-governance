import datetime


from cloud_governance.common.clouds.azure.cost_management.cost_management_operations import CostManagementOperations


def test_get_usage():
    """
    This method tests the azure usage results getting or not
    @return:
    """
    cost_management_operations = CostManagementOperations()
    end_date = datetime.datetime.now(datetime.UTC.utc) - datetime.timedelta(days=2)
    start_date = end_date - datetime.timedelta(days=1)
    granularity = 'Daily'
    scope = cost_management_operations.azure_operations.get_billing_profiles_list()[0]
    if scope:
        cost_usage_data = cost_management_operations.get_usage(scope=scope,
                                                               start_date=start_date, end_date=end_date,
                                                               granularity=granularity
                                                               )
        assert cost_usage_data
    else:
        assert False


def test_get_forecast():
    """
    This method tests the azure forecast results getting or not
    @return:
    """
    cost_management_operations = CostManagementOperations()
    end_date = datetime.datetime.now(datetime.UTC.utc) + datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=1)
    granularity = 'Daily'
    cost_forecast_data = cost_management_operations.get_forecast(scope=cost_management_operations.azure_operations.scope,
                                                                 start_date=start_date, end_date=end_date,
                                                                 granularity=granularity)
    assert cost_forecast_data
