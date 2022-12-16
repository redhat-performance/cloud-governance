import calendar
import datetime

import pytz
from azure.mgmt.costmanagement.models import QueryDataset, QueryAggregation, QueryTimePeriod

from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class CostManagementOperations:

    def __init__(self):
        self.azure_operations = AzureOperations()

    @logger_time_stamp
    def get_usage(self, start_date: datetime = '', end_date: datetime = '', granularity: str = 'Monthly'):
        """
        This method get the current usage based on month
        @return:
        """
        if not start_date and not end_date:
            end_date = datetime.datetime.now(pytz.UTC)
            start_date = end_date.replace(day=1)
        response = self.azure_operations.cost_mgmt_client.query.usage(scope=self.azure_operations.scope, parameters={
            'type': 'Usage', 'timeframe': 'Custom', 'time_period': QueryTimePeriod(from_property=start_date, to=end_date),
            'dataset': QueryDataset(granularity=granularity, aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum")
            })
        })
        return response.as_dict()

    @logger_time_stamp
    def get_forecast(self, start_date: datetime = '', end_date: datetime = '', granularity: str = 'Monthly'):
        """
        This method gets the forecast of next couple of months
        @param start_date:
        @param end_date:
        @param granularity:
        @return:
        """
        if not start_date and not end_date:
            current = datetime.datetime.now(pytz.UTC)
            start_date = (current - datetime.timedelta(30)).replace(day=1)
            end_date = (current + datetime.timedelta(60))
            month_end = calendar.monthrange(end_date.year, end_date.month)[1]
            end_date = end_date.replace(day=month_end)
        logger.info(f'StartDate: {start_date}, EndDate: {end_date}')
        response = self.azure_operations.cost_mgmt_client.forecast.usage(scope=self.azure_operations.scope, parameters={
            'type': 'ActualCost', 'timeframe': 'Custom',
            'time_period': QueryTimePeriod(from_property=start_date, to=end_date),
            'dataset': QueryDataset(granularity=granularity, aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            }), 'include_actual_cost': True, 'include_fresh_partial_cost': False
        }).as_dict()
        result = {'columns': response.get('columns'), 'rows': []}
        row_data = {}
        for data in response.get('rows'):
            data_date = data[1]
            if data_date in row_data:
                if row_data[data_date][2] == 'Actual' and data[2] == 'Forecast':
                    row_data[data_date][2] = data[2]
                row_data[data_date][0] += data[0]
            else:
                row_data[data_date] = data
        result['rows'] = list(row_data.values())
        return result
