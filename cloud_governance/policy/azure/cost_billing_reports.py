import datetime

from cloud_governance.common.clouds.azure.cost_management.cost_management_operations import CostManagementOperations
from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.common.google_drive.upload_to_gsheet import UploadToGsheet
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class CostBillingReports:
    """
    This class is responsible for generation cost billing report for Budget, Actual, Forecast
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.azure_operations = AzureOperations()
        self.cost_mgmt_operations = CostManagementOperations()
        self.elastic_upload = ElasticUpload()
        self.gdrive_operations = GoogleDriveOperations()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID')
        self.update_to_gsheet = UploadToGsheet()
        self.__cost_center, self.__allocated_budget, self.__years = self.update_to_gsheet.get_cost_center_budget_details(account_id=self.azure_operations.subscription_id)

    def get_common_data(self):
        """
        This method gives the common data to added
        @return:
        """
        upload_data = {}
        upload_data['AccountId'] = self.azure_operations.subscription_id
        upload_data['Account'] = self.azure_operations.account_name+'-'+self.azure_operations.cloud_name.title()
        upload_data['Budget'] = 0
        upload_data['AllocatedBudget'] = 0
        upload_data['CostCenter'] = self.__cost_center
        upload_data['CloudName'] = self.azure_operations.cloud_name
        return upload_data

    @logger_time_stamp
    def get_data_from_costs(self, cost_data_rows: list, cost_data_columns: list, cost_type: str, cost_billing_data: dict):
        """
        This method get the data from the cost
        @param cost_billing_data:
        @param cost_type:
        @param cost_data_rows:
        @param cost_data_columns:
        @return:
        """
        common_data = self.get_common_data()
        for index, item in enumerate(cost_data_rows):
            cost_data = {}
            start_date = ''
            for key, column in enumerate(cost_data_columns):
                if column.get('type') == 'Number':
                    if cost_type == 'Forecast':
                        cost_data[item[2]] = round(item[key], 2)
                    else:
                        cost_data[cost_type] = round(item[key], 2)
                else:
                    if column.get('type') == 'Datetime':
                        start_date = item[key].split('T')[0]
            if start_date not in cost_billing_data:
                if start_date.split('-')[0] in self.__years:
                    if 'Budget' in common_data:
                        common_data.pop('Budget')
                    if 'AllocatedBudget' in common_data:
                        common_data.pop('AllocatedBudget')
                    cost_data['Budget'] = round(self.__allocated_budget / 12, 3)
                    cost_data['AllocatedBudget'] = self.__allocated_budget
                cost_data['start_date'] = start_date
                cost_data.update(common_data)
                cost_data['index_id'] = f"""{cost_data['start_date']}-{cost_data['Account'].lower()}-{self.azure_operations.cloud_name.lower()}"""
                cost_data['timestamp'] = datetime.datetime.strptime(cost_data['start_date'], '%Y-%m-%d')
                cost_data['Month'] = datetime.datetime.strftime(cost_data['timestamp'], '%Y %b')
                cost_data['filter_date'] = cost_data['start_date'] + cost_data['Month'].split()[-1]
                cost_billing_data[cost_data['start_date']] = cost_data
            else:
                cost_billing_data[start_date].update(cost_data)
            if start_date:
                if 'Actual' not in cost_billing_data[start_date]:
                    cost_billing_data[start_date]['Actual'] = 0
                else:
                    if 'Forecast' not in cost_billing_data[start_date]:
                        cost_billing_data[start_date]['Forecast'] = 0
        return cost_billing_data

    @logger_time_stamp
    def collect_and_upload_cost_data(self):
        """
        This method collect and upload the data
        @return:
        """
        usage_data = self.cost_mgmt_operations.get_usage()
        forecast_data = self.cost_mgmt_operations.get_forecast()
        cost_billing_data = {}
        self.get_data_from_costs(cost_data_rows=usage_data.get('rows'), cost_data_columns=usage_data.get('columns'), cost_type='Actual', cost_billing_data=cost_billing_data)
        self.get_data_from_costs(cost_data_rows=forecast_data.get('rows'), cost_data_columns=forecast_data.get('columns'), cost_type='Forecast', cost_billing_data=cost_billing_data)
        cost_billing_data = dict(sorted(cost_billing_data.items()))
        uploaded_cost_data = list(cost_billing_data.values())
        self.elastic_upload.es_upload_data(items=uploaded_cost_data, set_index='index_id')
        upload_data = {
            'cloud_alias_name': f'{self.azure_operations.account_name}-azure',
            'cloud_name': 'AZURE',
            'cloud_data': uploaded_cost_data
        }
        self.update_to_gsheet.update_data(cloud_data=upload_data)
        return uploaded_cost_data

    def run(self):
        """
        This method runs the azure cost billing reports
        @return:
        """
        self.collect_and_upload_cost_data()
