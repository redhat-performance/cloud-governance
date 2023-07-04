import calendar
import datetime
import time

import pytz
from azure.core.exceptions import HttpResponseError
from azure.mgmt.costmanagement.models import QueryDataset, QueryAggregation, QueryTimePeriod, QueryGrouping

from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class CostManagementOperations:
    """This class for fetching the azure usage and forecast reports"""

    def __init__(self):
        self.azure_operations = AzureOperations()

    @logger_time_stamp
    def get_usage(self, scope: str, start_date: datetime = '', end_date: datetime = '', granularity: str = 'Monthly', **kwargs):
        """
        This method get the current usage based on month
        @return:
        """
        try:
            if not start_date and not end_date:
                end_date = datetime.datetime.now(pytz.UTC)
                start_date = (end_date - datetime.timedelta(days=30)).replace(day=1)
            response = self.azure_operations.cost_mgmt_client.query.usage(scope=scope, parameters={
                'type': 'Usage', 'timeframe': 'Custom', 'time_period': QueryTimePeriod(from_property=start_date, to=end_date),
                'dataset': QueryDataset(granularity=granularity, aggregation={
                    "totalCost": QueryAggregation(name="Cost", function="Sum")}, **kwargs
                )
            })
            return response.as_dict()
        except HttpResponseError as e:
            logger.error(e)
            if e.status_code == 429:
                time.sleep(10)
                return self.get_usage(scope, start_date=start_date, end_date=end_date, granularity=granularity, **kwargs)
        except Exception as err:
            logger.error(err)
        return []

    @logger_time_stamp
    def get_forecast(self, scope: str, start_date: datetime = '', end_date: datetime = '', granularity: str = 'Monthly', **kwargs):
        """
        This method gets the forecast of next couple of months
        @param start_date:
        @param end_date:
        @param granularity:
        @param scope:
        @return:
        """
        try:
            if not start_date and not end_date:
                current = datetime.datetime.now(pytz.UTC)
                start_date = (current - datetime.timedelta(60)).replace(day=1)
                end_date = (current + datetime.timedelta(365))
                month_end = calendar.monthrange(end_date.year, end_date.month)[1]
                end_date = end_date.replace(day=month_end)
            logger.info(f'StartDate: {start_date}, EndDate: {end_date}')
            response = self.azure_operations.cost_mgmt_client.forecast.usage(scope=scope, parameters={
                'type': 'ActualCost', 'timeframe': 'Custom',
                'time_period': QueryTimePeriod(from_property=start_date, to=end_date),
                'dataset': QueryDataset(granularity=granularity, aggregation={
                    "totalCost": QueryAggregation(name="Cost", function="Sum"),
                }, **kwargs), 'include_actual_cost': True, 'include_fresh_partial_cost': False
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
        except HttpResponseError as e:
            logger.error(e)
            if e.status_code == 429:
                time.sleep(10)
                return self.get_usage(scope, start_date=start_date, end_date=end_date, granularity=granularity, **kwargs)
        except Exception as err:
            logger.error(err)
        return []
