import datetime
import os

import pandas as pd

from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.sts.sts_oprations import STSOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.common.google_drive.upload_to_gsheet import UploadToGsheet


class CostBillingReports:
    """
    This class is responsible for generation cost billing report for Budget, Actual, Forecast
    """

    GRANULARITY = 'MONTHLY'
    COST_METRIC = 'UNBLENDED_COST'

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__cost_explorer_operations = CostExplorerOperations()
        self.elastic_upload = ElasticUpload()
        self.account_name, self.__cloud_name = IAMOperations().get_account_alias_cloud_name()
        self.__account_id = STSOperations().get_account_id()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID', '')
        self.gdrive_operations = GoogleDriveOperations()
        self.cost_center, self.__account_budget = self.get_cost_center_budget_details()
        self.update_to_gsheet = UploadToGsheet()

    def get_cost_center_budget_details(self):
        """
        This method returns the cost center & budget details
        @return:
        """
        file_path = '/tmp/Accounts.csv'
        if os.path.exists(file_path):
            self.gdrive_operations.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name='Accounts', file_path=f'/tmp')
        accounts_df = pd.read_csv(file_path)
        account_row = accounts_df[accounts_df['AccountId'] == self.__account_id].reset_index().to_dict(orient='records')
        if account_row:
            return account_row[0].get('CostCenter', 0), float(account_row[0].get('Budget', '0').replace(',', ''))
        return 0, 0

    def get_date_ranges(self, days: int = 0):
        """
        This method returns the date ranges
        @param days:
        @return:
        """
        end_date = datetime.datetime.now()+datetime.timedelta(1)
        if days == 0:
            start_date = f"{end_date.year}-{end_date.month-1}-01"
        else:
            start_date = end_date.strftime('%Y-%m-%d')
            end_date = end_date + datetime.timedelta(days)
        end_date = end_date.strftime('%Y-%m-%d')
        return start_date, end_date

    def filter_cost_usage_data(self, cost_usage_data: list, cost_metric: str):
        """
        This method filter and removes the unwanted data
        @param cost_metric:
        @param cost_usage_data:
        @return:
        """
        cost_data = {}
        for cost_usage in cost_usage_data:
            data = {}
            data['Actual'] = round(float(cost_usage.get('Total').get(cost_metric).get('Amount')), 3)
            data['Account'] = self.account_name
            data['start_date'] = str(cost_usage.get('TimePeriod').get('Start'))
            data['index_id'] = f"""{data['start_date']}-{data['Account'].lower()}"""
            data['timestamp'] = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d')
            data['Month'] = datetime.datetime.strftime(data['timestamp'], '%Y %b')
            data['Budget'] = round(self.__account_budget/12, 3)
            data['AllocatedBudget'] = self.__account_budget
            data['CostCenter'] = self.cost_center
            data['CloudName'] = self.__cloud_name
            data['Forecast'] = 0
            data['AccountId'] = self.__account_id
            data['filter_date'] = data['start_date']+data['Month'].strip()
            cost_data[data['start_date']] = data
        return cost_data

    def append_forecasting_data(self, cost_usage_data: dict, cost_forecast_data: list):
        """
        This method appends the fore
        @param cost_forecast_data:
        @param cost_usage_data:
        @return:
        """
        for cost_forecast in cost_forecast_data:
            start_date = str((cost_forecast.get('TimePeriod').get('Start')))
            cost = round(float(cost_forecast.get('MeanValue')), 3)
            if start_date in cost_usage_data:
                cost_usage_data[start_date]['Forecast'] = cost
            else:
                data = {}
                data['AccountId'] = self.__account_id
                data['Actual'] = 0
                data['Forecast'] = cost
                data['Account'] = self.account_name
                data['start_date'] = str((cost_forecast.get('TimePeriod').get('Start')))
                data['index_id'] = f"""{data['start_date']}-{data['Account'].lower()}"""
                data['timestamp'] = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d')
                data['Month'] = datetime.datetime.strftime(data['timestamp'], '%Y %b')
                data['Budget'] = round(self.__account_budget/12, 3)
                data['AllocatedBudget'] = self.__account_budget
                data['CostCenter'] = self.cost_center
                data['CloudName'] = self.__cloud_name
                data['filter_date'] = data['start_date']+data['Month']
                cost_usage_data.setdefault(start_date, data)
        return cost_usage_data

    def get_cost_usage_of_month(self):
        """
        This method get cost usage of this month
        @rtype: object
        """
        start_date, end_date = self.get_date_ranges()
        cost_data = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity=self.GRANULARITY)
        start_date, end_date = self.get_date_ranges(days=360)
        cost_forecast_data = self.__cost_explorer_operations.get_cost_forecast(start_date=start_date, end_date=end_date, granularity=self.GRANULARITY, cost_metric=self.COST_METRIC)
        cost_filtered_data = self.filter_cost_usage_data(cost_usage_data=cost_data['ResultsByTime'], cost_metric=self.COST_METRIC.title().replace('_', ''))
        self.append_forecasting_data(cost_usage_data=cost_filtered_data, cost_forecast_data=cost_forecast_data['ForecastResultsByTime'])
        # self.elastic_upload.es_upload_data(items=list(cost_filtered_data.values()), set_index='index_id')
        upload_data = {
            'cloud_alias_name': self.account_name,
            'cloud_name': 'AWS',
            'cloud_data': list(cost_filtered_data.values())
        }
        self.update_to_gsheet.update_data(cloud_data=upload_data)
        return cost_filtered_data

    def run(self):
        """
        This method run the methods
        @return:
        """
        self.get_cost_usage_of_month()
