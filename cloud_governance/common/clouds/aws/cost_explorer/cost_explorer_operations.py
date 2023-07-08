from datetime import datetime, timedelta

import boto3

from cloud_governance.common.logger.init_logger import logger


class CostExplorerOperations:
    """
    This class extracts the price data from AWS Cost Explorer
    """

    START_DAY = 1
    END_DAY = 31
    DIMENSIONS = 'Dimensions'
    KEY = 'Key'
    VALUES = 'Values'
    PURCHASE_TYPE = 'PURCHASE_TYPE'
    SPOT_INSTANCES = 'Spot Instances'
    FILTER = 'Filter'
    PURCHASE_OPTIONS = ['On Demand Instances', 'Savings Plans', SPOT_INSTANCES, 'Standard Reserved Instances']
    CE_COST_TYPES = {'CHARGETYPE': 'RECORD_TYPE', 'PURCHASETYPE': PURCHASE_TYPE}
    CE_FILTER_TEMPLATE = {
        DIMENSIONS: {
            KEY: '',
            VALUES: []
        }
    }
    CE_COST_FILTERS = {'SPOT': {KEY: PURCHASE_TYPE, VALUES: [SPOT_INSTANCES]}}

    def __init__(self, ce_client=''):
        self.cost_explorer_client = boto3.client('ce') if not ce_client else ce_client

    def __get_ce_tag_filters(self, tag: str, ce_default_filter: dict):
        """
        This method returns the ce filter values
        :return:
        """
        if ':' in tag:
            tag, tag_filter = tag.split(':')
            tag_filter = tag_filter.upper()
            ce_filter = self.CE_FILTER_TEMPLATE
            if tag_filter in self.CE_COST_FILTERS:
                ce_filter[self.DIMENSIONS][self.KEY] = self.CE_COST_FILTERS[tag_filter][self.KEY]
                ce_filter[self.DIMENSIONS][self.VALUES] = self.CE_COST_FILTERS[tag_filter][self.VALUES]
            if ce_default_filter:
                ce_default_filter = {
                    'And': [
                        ce_default_filter,
                        ce_filter
                    ]
                }
            else:
                ce_default_filter = ce_filter
        return ce_default_filter

    def get_ce_report_filter_data(self, ce_response: dict, tag_name: str):
        """
        This method returns data filter by tag_name
        :param tag_name:
        :param ce_response:
        :return:
        """
        data = {}
        if ce_response.get('ResultsByTime'):
            for results_by_time in ce_response.get('ResultsByTime'):
                start_time = results_by_time.get('TimePeriod').get('Start')
                for group in results_by_time.get('Groups'):
                    name = group.get('Keys')[0].split('$')[-1].strip().replace(' ', '-') if group.get('Keys') else ''
                    amount = group.get('Metrics').get('UnblendedCost').get('Amount') if group.get('Metrics') else 0
                    index_id = "%s-%s" % (start_time, name)
                    data[index_id] = {
                        tag_name: amount,
                        'ce_match_id': index_id,
                        'start_date': start_time
                    }
        if ce_response.get('DimensionValueAttributes'):
            for dimension_values in ce_response.get('DimensionValueAttributes'):
                account_id = dimension_values.get("Value")
                account = dimension_values.get('Attributes').get('description')
                for key_index_id in data.keys():
                    if account_id in key_index_id:
                        index_id = f'{data[key_index_id]["start_date"]}-{account}'.lower()
                        data[key_index_id].update({'Account': account, 'index_id': index_id})
        return data

    def get_filter_data(self, ce_data: list, tag_name: str = '', group_by: bool = True):
        """
        This method filter the cost_explorer_data
        :param group_by:
        :param tag_name:
        :param ce_data:
        :return:
        """
        user_cost_response = {}
        if group_by:
            for data in ce_data:
                for cost_group in data.get('Groups'):
                    user = cost_group.get('Keys')[0].split('$')[-1]
                    user = user if user else 'REFUND'
                    user_cost = float(cost_group.get('Metrics').get('UnblendedCost').get('Amount'))
                    if user in user_cost_response:
                        user_cost_response[user]['Cost'] += user_cost
                    else:
                        user_cost_response[user] = {tag_name: user, 'Cost': user_cost}
            return list(user_cost_response.values())
        else:
            total_cost = 0
            for data in ce_data:
                total_cost += float(data.get('Total').get('UnblendedCost').get('Amount'))
            return total_cost

    def get_cost_by_tags(self, tag: str, granularity: str = 'DAILY', cost_metric: str = 'UnblendedCost',
                         start_date: str = '', end_date: str = '', **kwargs):
        """
        This method extracts the price by Tag provided
        @return:
        """
        if not start_date and not end_date:
            end_date = datetime.now() + timedelta(self.START_DAY)
            start_date = end_date - timedelta(self.END_DAY)
            start_date = str(start_date.strftime('%Y-%m-%d'))
            end_date = str(end_date.strftime('%Y-%m-%d'))
        if tag.upper() in self.CE_COST_TYPES:
            return self.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=granularity,
                                                    GroupBy=[{'Type': 'DIMENSION', 'Key': self.CE_COST_TYPES[tag.upper()]}], **kwargs)
        else:
            kwargs[self.FILTER] = self.__get_ce_tag_filters(tag=tag, ce_default_filter=kwargs.get(self.FILTER))
            if ':' in tag:
                tag, tag_filter = tag.split(':')
            return self.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=granularity,
                                                    cost_metric=cost_metric, GroupBy=[{'Type': 'TAG', 'Key': tag}], **kwargs)

    def get_cost_and_usage_from_aws(self, start_date: str, end_date: str, granularity: str = 'DAILY',
                                    cost_metric: str = 'UnblendedCost', **kwargs):
        """
        This method returns the cost and usage reports
        @param start_date:
        @param end_date:
        @param granularity:
        @param cost_metric:
        @param kwargs:
        @return:
        """
        try:
            if self.FILTER in kwargs and not kwargs.get('Filter'):
                kwargs.pop('Filter')
            usage_cost = {}
            response = self.cost_explorer_client.get_cost_and_usage(TimePeriod={
                'Start': start_date,
                'End': end_date
            }, Granularity=granularity, Metrics=[cost_metric], **kwargs)
            usage_cost['GroupDefinitions'] = response.get('GroupDefinitions')
            usage_cost['ResultsByTime'] = response.get('ResultsByTime')
            usage_cost['DimensionValueAttributes'] = response.get('DimensionValueAttributes')
            while response.get('NextPageToken'):
                response = self.cost_explorer_client.get_cost_and_usage(TimePeriod={
                    'Start': start_date,
                    'End': end_date
                }, Granularity=granularity, Metrics=[cost_metric], NextPageToken=response.get('NextPageToken'), **kwargs)
                usage_cost['ResultsByTime'].extend(response.get('ResultsByTime'))
                usage_cost['DimensionValueAttributes'].extend(response.get('DimensionValueAttributes'))
            return usage_cost
        except Exception as err:
            logger.error(err)
            return {
                'ResultsByTime': [],
                'DimensionValueAttributes': [],
                'GroupDefinitions': [],
            }

    def get_cost_forecast(self, start_date: str, end_date: str, granularity: str, cost_metric: str, **kwargs):
        """
        This method returns the cost forecasting
        @param start_date:
        @param end_date:
        @param granularity:
        @param cost_metric:
        @return:
        """
        try:
            return self.cost_explorer_client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity=granularity,
                Metric=cost_metric, **kwargs
            )
        except Exception as err:
            logger.error(err)
            return {'Total': {'Amount': 0}, 'ForecastResultsByTime': []}
