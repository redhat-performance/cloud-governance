import calendar
import datetime
import time

import pytz
from azure.core.exceptions import HttpResponseError
from azure.mgmt.costmanagement.models import QueryTimePeriod

from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class CostManagementOperations:
    """This class for fetching the azure usage and forecast reports"""

    def __init__(self):
        self.azure_operations = AzureOperations()

    def __get_query_dataset(self, grouping: list, tags: dict, granularity: str):
        """
        This method returns the dataset
        :param grouping:
        :type grouping:
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        query_dataset = {"aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                         "granularity": granularity,
                         }
        if tags:
            filter_tags = {}
            if len(tags) > 2:
                for key, value in tags.items():
                    and_filter = {'tags': {'name': key.lower(), "operator": "In", 'values': [value.lower()]}}
                    filter_tags.setdefault('and', []).append(and_filter)
            else:
                for key, value in tags.items():
                    filter_tags = {'tags': {'name': key.lower(), "operator": "In", 'values': [value.lower()]}}
            query_dataset['filter'] = filter_tags
        if grouping:
            filter_grouping = []
            for group in grouping:
                if isinstance(group, dict):
                    filter_grouping.append({"name": group['name'], "type": group['type']})
                else:
                    filter_grouping.append({"name": group.lower(), "type": "TagKey"})
            query_dataset['grouping'] = filter_grouping
        return query_dataset

    @logger_time_stamp
    def get_usage(self, scope: str, start_date: datetime = None, end_date: datetime = None,
                  granularity: str = 'Monthly', tags: dict = None, grouping: list = None, **kwargs):
        """
        This method get the current usage based on month
        :param scope:
        :param start_date:
        :param end_date:
        :param granularity:
        :param tags:
        :param grouping:
        :param kwargs:
        :return:
        """
        try:
            if not start_date and not end_date:
                end_date = datetime.datetime.now(pytz.UTC)
                start_date = (end_date - datetime.timedelta(days=30)).replace(day=1)
            response = self.azure_operations.cost_mgmt_client.query.usage(scope=scope, parameters={
                'type': 'Usage', 'timeframe': 'Custom',
                'time_period': QueryTimePeriod(from_property=start_date, to=end_date),
                'dataset': self.__get_query_dataset(grouping=grouping, tags=tags, granularity=granularity)
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
    def get_forecast(self, scope: str, start_date: datetime = '', end_date: datetime = '', granularity: str = 'Monthly',
                     tags: dict = None, grouping: list = None, **kwargs):
        """
        This method gets the forecast of next couple of months
        @param start_date:
        @param end_date:
        @param granularity:
        @param scope:
        @param tags:
        @param grouping:
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
                        'dataset': self.__get_query_dataset(grouping=grouping, tags=tags, granularity=granularity),
                        'include_actual_cost': True, 'include_fresh_partial_cost': False
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

    def get_filter_data(self, cost_data: dict, tag_name: str = 'User'):
        """
        This method returns the cost data in dict format
        :param tag_name:
        :type tag_name:
        :param cost_data:
        :type cost_data:
        :return:
        :rtype:
        """
        output_list = self.get_prettify_data(cost_data)
        users_list = {}
        for item in output_list:
            tag_value = item.get('TagValue')
            if tag_value not in users_list:
                users_list[tag_value] = {}
                users_list[tag_value]['Cost'] = item.get('Cost')
            else:
                users_list[tag_value]['Cost'] = users_list[tag_value]['Cost'] + item.get('Cost')
        users_cost = []
        for value, cost in users_list.items():
            users_cost.append({'User': value, 'Cost': cost.get('Cost')})
        return users_cost

    def get_prettify_data(self, cost_data: dict):
        """
        This method returns the prettify data
        :param cost_data:
        :type cost_data:
        :return:
        :rtype:
        """
        columns = cost_data.get('columns')
        columns_data = [column.get('name') for column in columns]
        rows = cost_data.get('rows')
        rows_data = [dict(zip(columns_data, row)) for row in rows]
        return rows_data

    def get_total_cost(self, cost_data: dict):
        """
        This method returns the total cost of the data dict
        :param cost_data:
        :type cost_data:
        :return:
        :rtype:
        """
        output_list = self.get_prettify_data(cost_data)
        total_sum = 0
        for item in output_list:
            total_sum += item.get('Cost')
        return total_sum
