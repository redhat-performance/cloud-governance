import datetime

import pytz
from azure.mgmt.costmanagement.models import QueryGrouping, QueryFilter, QueryComparisonExpression

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
        self.__total_account = self.__environment_variables_dict.get('TOTAL_ACCOUNTS', '')
        self.azure_operations = AzureOperations()
        self.cost_mgmt_operations = CostManagementOperations()
        self.elastic_upload = ElasticUpload()
        self.gdrive_operations = GoogleDriveOperations()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID')
        self.update_to_gsheet = UploadToGsheet()
        self.__cost_center, self.__allocated_budget, self.__years, self.__owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=self.azure_operations.subscription_id, dir_path='/tmp')
        self.__common_data = self.get_common_data()

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
        upload_data['CostCenter'] = int(self.__cost_center)
        upload_data['CloudName'] = self.azure_operations.cloud_name
        upload_data['Owner'] = self.__owner
        return upload_data

    @logger_time_stamp
    def get_data_from_costs(self, cost_data_rows: list, cost_data_columns: list, cost_type: str, cost_billing_data: dict, subscription_id: str = '', account_name: str = '', cost_center: int = 0):
        """
        This method get the data from the cost
        @param cost_billing_data:
        @param cost_type:
        @param cost_data_rows:
        @param cost_data_columns:
        @param subscription_id:
        @return:
        """
        common_data = self.__common_data
        index_id = ''
        common_data["AccountId"] = subscription_id
        if account_name:
            common_data['Account'] = account_name
        if cost_center > 0:
            common_data['CostCenter'] = cost_center
        if subscription_id:
            cost_center, allocated_budget, years, owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=subscription_id, dir_path='/tmp')
            if cost_center:
                common_data['CostCenter'] = int(cost_center)
                common_data['Owner'] = owner
            else:
                common_data['Owner'] = owner
        else:
            allocated_budget, years = self.__allocated_budget, self.__years
        for index, item in enumerate(cost_data_rows):
            cost_data = {}
            start_date = ''
            for key, column in enumerate(cost_data_columns):
                if column.get('type') == 'Number':
                    if cost_type == 'Forecast':
                        cost_data[item[2]] = round(item[key], 2)
                    else:
                        cost_data[cost_type] = round(item[key], 2)
                elif column.get('name') == 'SubscriptionName':
                    common_data['Account'] = item[key]
                elif column.get('name') == 'SubscriptionId':
                    common_data['AccountId'] = item[key]
                    cost_center, allocated_budget, years, owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=item[key], dir_path='/tmp')
                    if cost_center:
                        common_data['CostCenter'] = int(cost_center)
                        common_data['Owner'] = owner
                    else:
                        common_data['Owner'] = owner
                else:
                    if column.get('type') == 'Datetime':
                        start_date = item[key].split('T')[0]
            index_id = f'{start_date}-{common_data["AccountId"]}'
            if index_id not in cost_billing_data:
                if start_date.split('-')[0] in years:
                    if 'Budget' in common_data:
                        common_data.pop('Budget')
                    if 'AllocatedBudget' in common_data:
                        common_data.pop('AllocatedBudget')
                cost_data['Budget'] = round(allocated_budget / 12, 3)
                cost_data['AllocatedBudget'] = allocated_budget
                cost_data['start_date'] = start_date
                cost_data.update(common_data)
                cost_data['index_id'] = f"""{cost_data['start_date']}-{cost_data['AccountId']}"""
                cost_data['timestamp'] = datetime.datetime.strptime(cost_data['start_date'], '%Y-%m-%d')
                cost_data['Month'] = datetime.datetime.strftime(cost_data['timestamp'], '%Y %b')
                cost_data['filter_date'] = f"{cost_data['start_date']}-{cost_data['Month'].split()[-1]}"
                cost_billing_data[index_id] = cost_data
            else:
                cost_billing_data[index_id].update(cost_data)
            if start_date:
                if 'Actual' not in cost_billing_data[index_id]:
                    cost_billing_data[index_id]['Actual'] = 0
                else:
                    if 'Forecast' not in cost_billing_data[index_id]:
                        cost_billing_data[index_id]['Forecast'] = 0
        return cost_billing_data

    def get_total_billing_accounts(self):
        """
        This method returns the data of all billing accounts
        """
        cost_billing_data = {}
        for profile in self.azure_operations.get_billing_profiles():
            profile = profile.as_dict()
            scope = profile.get('id')
            self.__common_data['AccountProfile'] = profile.get('display_name')
            cost_center = int(profile.get('display_name').split('(CC ')[-1].split(')')[0])
            self.__common_data['CostCenter'] = cost_center
            filters = {
                'grouping': [QueryGrouping(type='Dimension', name='SubscriptionName'),
                             QueryGrouping(type='Dimension', name='SubscriptionId')]
            }
            usage_data = self.cost_mgmt_operations.get_usage(scope=scope, **filters)
            subscription_ids = []
            if usage_data.get('rows'):
                subscription_ids = [[id[3], id[2]] for id in usage_data.get('rows')]
                self.get_data_from_costs(cost_data_rows=usage_data.get('rows'), cost_data_columns=usage_data.get('columns'), cost_type='Actual',
                                         cost_billing_data=cost_billing_data)
            for subscription in subscription_ids:
                query_filter = {
                    'filter': QueryFilter(dimensions=QueryComparisonExpression(name='SubscriptionId', operator='in',
                                                                               values=[subscription[0]]))}
                forecast_data = self.cost_mgmt_operations.get_forecast(scope=scope, **query_filter)
                if forecast_data and forecast_data.get('rows'):
                    self.get_data_from_costs(cost_data_rows=forecast_data.get('rows'),
                                             cost_data_columns=forecast_data.get('columns'), cost_type='Forecast',
                                             cost_billing_data=cost_billing_data, subscription_id=subscription[0],
                                             account_name=subscription[1], cost_center=cost_center)
            self.__common_data = self.get_common_data()
        return cost_billing_data

    @logger_time_stamp
    def collect_and_upload_cost_data(self):
        """
        This method collect and upload the data
        @return:
        """
        cost_billing_data = {}
        if not self.__total_account:
            usage_data = self.cost_mgmt_operations.get_usage(scope=self.azure_operations.scope)
            forecast_data = self.cost_mgmt_operations.get_forecast(scope=self.azure_operations.scope)
            if usage_data:
                self.get_data_from_costs(cost_data_rows=usage_data.get('rows'), cost_data_columns=usage_data.get('columns'), cost_type='Actual', cost_billing_data=cost_billing_data)
            if forecast_data:
                self.get_data_from_costs(cost_data_rows=forecast_data.get('rows'), cost_data_columns=forecast_data.get('columns'), cost_type='Forecast', cost_billing_data=cost_billing_data, subscription_id=self.azure_operations.subscription_id)
        else:
            cost_billing_data = self.get_total_billing_accounts()
        if cost_billing_data:
            cost_billing_data = dict(sorted(cost_billing_data.items()))
            uploaded_cost_data = list(cost_billing_data.values())
            self.elastic_upload.es_upload_data(items=uploaded_cost_data, set_index='index_id')
            if not self.__total_account:
                upload_data = {
                    'cloud_alias_name': f'{self.azure_operations.account_name}-azure',
                    'cloud_name': 'AZURE',
                    'cloud_data': uploaded_cost_data
                }
                self.update_to_gsheet.update_data(cloud_data=upload_data)
        return list(cost_billing_data.values())

    def run(self):
        """
        This method runs the azure cost billing reports
        @return:
        """
        self.collect_and_upload_cost_data()
