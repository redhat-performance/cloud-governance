import os
from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class CostForecasting:

    def __init__(self):
        self.ce_operations = CostExplorerOperations()
        self.start_date = os.environ.get('start_date', '')  # yyyy-mm-dd
        self.end_date = os.environ.get('end_date', '')  # yyyy-mm-dd
        self.granularity = os.environ.get('granularity', 'DAILY')
        self.cost_metric = os.environ.get('cost_metric', 'UNBLENDED_COST')
        self.file_name = os.environ.get('file_name', '')
        self._elastic_upload = ElasticUpload()
        self._iam_client = boto3.client('iam')

    def get_account_alias(self):
        """
        This method returns the aws account alias
        @return:
        """
        account_alias = self._iam_client.list_account_aliases()['AccountAliases']
        if account_alias:
            return account_alias[0].lower()
        return os.environ.get('account', '')

    def modify_forecast_data(self, forecast_data: dict):
        """
        This method arrange the data based on granularity
        @param forecast_data:
        @return:
        """
        account_name = self.get_account_alias()
        granularity_data = []
        for data in forecast_data.get('ForecastResultsByTime'):
            start_date = data.get('TimePeriod').get('Start')
            index_data = {
                "Granularity": self.granularity,
                "start_date": f'{str(start_date)}-{self.granularity.lower()}-{account_name}',
                "timestamp": datetime.strptime(start_date, '%Y-%m-%d'),
                "Cost": round(float(data.get('MeanValue')), 3),
                "Weekday": datetime.strptime(start_date, '%Y-%m-%d').strftime('%A'),
                "Account": account_name.upper()
            }
            granularity_data.append(index_data)
        return granularity_data

    @logger_time_stamp
    def aws_cost_forecasting(self):
        """
        This methods get the forecast from the AWS Cost Explorer
        @return:
        """
        forecast_data = self.ce_operations.get_aws_cost_forecast(granularity=self.granularity, cost_metric=self.cost_metric, start_date=self.start_date, end_date=self.end_date)
        granularity_data = self.modify_forecast_data(forecast_data)
        self._elastic_upload.es_upload_data(items=granularity_data, set_index='start_date')
        return granularity_data

    def run(self):
        """
        This method runs the cost forecasting methods
        @return:
        """
        return self.aws_cost_forecasting()
