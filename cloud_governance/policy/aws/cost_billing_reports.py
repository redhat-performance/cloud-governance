import datetime
import operator
import tempfile
from operator import sub, add

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
    MONTHS = 12
    END_DAY = 31
    FORECAST_DAYS = 360

    def __init__(self):
        try:
            self._environment_variables_dict = environment_variables.environment_variables_dict
            self.__cost_explorer_operations = CostExplorerOperations()
            self.elastic_upload = ElasticUpload()
            self.account_name, self.__cloud_name = IAMOperations().get_account_alias_cloud_name()
            self.__account_id = STSOperations().get_account_id()
            self.__gsheet_id = self._environment_variables_dict.get('SPREADSHEET_ID', '')
            self.gdrive_operations = GoogleDriveOperations()
            self.update_to_gsheet = UploadToGsheet()
            self.cost_center, self.__account_budget, self.__years, self.__owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=self.__account_id)
        except:
            pass

    def __get_start_date(self, end_date: datetime, days: int, operation: operator) -> datetime:
        """
        This method returns start_date
        @param operation:
        @param end_date:
        @param days:
        @return:
        """
        return operation(end_date, datetime.timedelta(days=days))

    def get_date_ranges(self, days: int = 0):
        """
        This method returns the date ranges
        @param days:
        @return:
        """
        end_date = datetime.datetime.now()+datetime.timedelta(1)
        if days == 0:
            start_date = self.__get_start_date(end_date=end_date, days=self.END_DAY, operation=sub).replace(day=1).strftime('%Y-%m-%d')
        else:
            start_date = end_date.strftime('%Y-%m-%d')
            end_date = self.__get_start_date(end_date=end_date, days=days, operation=add)
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
            start_year = str(cost_usage.get('TimePeriod').get('Start')).split('-')[0]
            data = {}
            data['Actual'] = round(float(cost_usage.get('Total').get(cost_metric).get('Amount')), 3)
            data['Account'] = self.account_name
            data['start_date'] = str(cost_usage.get('TimePeriod').get('Start'))
            data['index_id'] = f"""{data['start_date']}-{data['Account'].lower()}"""
            data['timestamp'] = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d')
            data['Month'] = datetime.datetime.strftime(data['timestamp'], '%Y %b')
            if start_year in self.__years:
                data['Budget'] = round(self.__account_budget/self.MONTHS, 3)
                data['AllocatedBudget'] = self.__account_budget
            else:
                data['Budget'] = 0
                data['AllocatedBudget'] = 0
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
            start_year = str(cost_forecast.get('TimePeriod').get('Start')).split('-')[0]
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
                if start_year in self.__years:
                    data['Budget'] = round(self.__account_budget / self.MONTHS, 3)
                    data['AllocatedBudget'] = self.__account_budget
                else:
                    data['Budget'] = 0
                    data['AllocatedBudget'] = 0
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
        start_date, end_date = self.get_date_ranges(days=self.FORECAST_DAYS)
        cost_forecast_data = self.__cost_explorer_operations.get_cost_forecast(start_date=start_date, end_date=end_date, granularity=self.GRANULARITY, cost_metric=self.COST_METRIC)
        cost_filtered_data = self.filter_cost_usage_data(cost_usage_data=cost_data['ResultsByTime'], cost_metric=self.COST_METRIC.title().replace('_', ''))
        self.append_forecasting_data(cost_usage_data=cost_filtered_data, cost_forecast_data=cost_forecast_data['ForecastResultsByTime'])
        self.elastic_upload.es_upload_data(items=list(cost_filtered_data.values()), set_index='index_id')
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
