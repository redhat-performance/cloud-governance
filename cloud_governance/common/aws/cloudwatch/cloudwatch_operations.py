from datetime import datetime, timedelta

import boto3


class CloudWatchOperations:
    """
    This class perform the cloudwatch operations
    methods
    1. get_metric_data
    """

    def __init__(self, region: str = 'us-east-2'):
        self._region = region
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=self._region)

    def _create_metric_lists(self, resource_id: str, resource_type: str, namespace: str, metric_names: dict, statistic: str):
        """
        This method create the metrics from metric resources
        @param resource_id:
        @param resource_type:
        @param namespace:
        @param metric_names:
        @param statistic:
        @return:
        """
        metric_lists = []
        for index, (metric_name, unit) in enumerate(metric_names.items()):
            metric_lists.append(
                {
                    'Id': f'metric{index}',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': [{'Name': resource_type, 'Value': resource_id}]
                        },
                        'Period': 86400,
                        'Stat': statistic,
                        'Unit': unit
                    },
                }
            )
        return metric_lists

    def get_metric_data(self, start_time: datetime, end_time: datetime, resource_id: str, resource_type: str,
                        namespace: str, metric_names: dict, statistic: str):
        """
        This method returns metrics of the specified resource and metrics
        @param start_time:
        @param end_time:
        @param resource_id:
        @param resource_type:
        @param namespace:
        @param metric_names:
        @param statistic:
        @return:
        """
        metric_lists = self._create_metric_lists(resource_id=resource_id, resource_type=resource_type,
                                                 namespace=namespace, metric_names=metric_names, statistic=statistic)
        return self.cloudwatch_client.get_metric_data(StartTime=start_time, EndTime=end_time,
                                                      MetricDataQueries=metric_lists)
