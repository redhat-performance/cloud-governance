import json
from datetime import datetime, timedelta

import boto3

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class CostExplorerOperations:
    """
    This class extracts the price data from AWS Cost Explorer
    """
    GRANULARITY_DAILY_DAYS = 91
    GRANULARITY_MONTHLY_DAYS = 360

    def __init__(self):
        self.cost_explorer_client = boto3.client('ce')

    def get_cost_by_tags(self, tag: str, granularity: str = 'DAILY', cost_metric: str = 'UnblendedCost', start_date: str = '', end_date: str = ''):
        """
        This method extracts the price by Tag provided
        @return:
        """
        if not start_date and not end_date:
            end_date = datetime.now() - timedelta(1)
            start_date = end_date - timedelta(1)
            start_date = str(start_date.strftime('%Y-%m-%d'))
            end_date = str(end_date.strftime('%Y-%m-%d'))
        return self.cost_explorer_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=[cost_metric],
            GroupBy=[{'Type': 'TAG', 'Key': tag}]
        )

    @logger_time_stamp
    def get_aws_cost_forecast(self, granularity: str = 'DAILY', cost_metric: str = 'UNBLENDED_COST', start_date: str = '', end_date: str = ''):
        if granularity == 'DAILY':
            days = self.GRANULARITY_DAILY_DAYS
        else:
            days = self.GRANULARITY_MONTHLY_DAYS
        if not start_date and not end_date:
            start_date = datetime.now()
            end_date = start_date + timedelta(days)
            start_date = str(start_date.strftime('%Y-%m-%d'))
            end_date = str(end_date.strftime('%Y-%m-%d'))
        return self.get_cost_forecast(start_date=start_date, end_date=end_date, granularity=granularity, cost_metric=cost_metric)

    @logger_time_stamp
    def get_cost_forecast(self, start_date: str, end_date: str, granularity: str, cost_metric: str):
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
            Metric=cost_metric
        )
