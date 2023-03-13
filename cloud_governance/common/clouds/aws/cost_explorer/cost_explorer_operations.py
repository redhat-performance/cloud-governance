from datetime import datetime, timedelta

import boto3


class CostExplorerOperations:
    """
    This class extracts the price data from AWS Cost Explorer
    """

    START_DAY = 1
    END_DAY = 31
    PURCHASE_OPTIONS = ['On Demand Instances', 'Savings Plans', 'Spot Instances', 'Standard Reserved Instances']

    def __init__(self, ce_client=''):
        self.cost_explorer_client = boto3.client('ce') if not ce_client else ce_client

    def get_cost_by_tags(self, tag: str, granularity: str = 'DAILY', cost_metric: str = 'UnblendedCost',
                         start_date: str = '', end_date: str = ''):
        """
        This method extracts the price by Tag provided
        @return:
        """
        if not start_date and not end_date:
            end_date = datetime.now() + timedelta(self.START_DAY)
            start_date = end_date - timedelta(self.END_DAY)
            start_date = str(start_date.strftime('%Y-%m-%d'))
            end_date = str(end_date.strftime('%Y-%m-%d'))
        if tag.upper() == 'ChargeType'.upper():
            return self.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=granularity,
                                                    GroupBy=[{'Type': 'DIMENSION', 'Key': 'RECORD_TYPE'}])
        elif tag.upper() == 'PURCHASETYPE':
            return self.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=granularity,
                                                    GroupBy=[{'Type': 'DIMENSION', 'Key': 'PURCHASE_TYPE'}])
        else:
            return self.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=granularity,
                                                    cost_metric=cost_metric, GroupBy=[{'Type': 'TAG', 'Key': tag}])

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

    def get_cost_forecast(self, start_date: str, end_date: str, granularity: str, cost_metric: str, **kwargs):
        """
        This method return the cost forecasting
        @param start_date:
        @param end_date:
        @param granularity:
        @param cost_metric:
        @return:
        """
        return self.cost_explorer_client.get_cost_forecast(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metric=cost_metric, **kwargs
        )
