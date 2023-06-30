import datetime

import pytest

from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations


@pytest.mark.skip(reason='Read Only')
def test_get_cost_and_usage_from_aws():
    cost_explorer_operations = CostExplorerOperations()
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(1)
    start_date = str(start_date.strftime('%Y-%m-%d'))
    end_date = str(end_date.strftime('%Y-%m-%d'))
    aws_usage = cost_explorer_operations.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date)
    assert aws_usage


@pytest.mark.skip(reason='Read Only')
def test_get_cost_forecast():
    cost_explorer_operations = CostExplorerOperations()
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(1)
    start_date = str(start_date.strftime('%Y-%m-%d'))
    end_date = str(end_date.strftime('%Y-%m-%d'))
    aws_forecast = cost_explorer_operations.get_cost_forecast(start_date=start_date, end_date=end_date, granularity='MONTHLY', cost_metric='UNBLENDED_COST')
    assert aws_forecast
