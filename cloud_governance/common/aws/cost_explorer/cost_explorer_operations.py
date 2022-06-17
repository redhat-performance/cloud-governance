import json
from datetime import datetime, timedelta

import boto3


class CostExplorerOperations:
    """
    This class extracts the price data from AWS Cost Explorer
    """

    def __init__(self):
        self.cost_explorer_client = boto3.client('ce')

    def get_daily_cost_usage(self, tag: str, metrics_type: str):
        """
        This method extracts the price by Tag provided
        @return:
        """
        today = datetime.now()
        start_time = today - timedelta(1)
        today = str(today.strftime('%Y-%m-%d'))
        start_time = str(start_time.strftime('%Y-%m-%d'))
        return self.cost_explorer_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_time,
                'End': today
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'TAG', 'Key': tag}]
        )
