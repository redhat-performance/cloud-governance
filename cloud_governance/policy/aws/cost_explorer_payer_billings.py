import copy
import datetime
from ast import literal_eval

import boto3
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.policy.aws.cost_billing_reports import CostBillingReports


class CostExplorerPayerBillings(CostBillingReports):
    """This class is responsible for generation cost billing report for Budget, Actual, Forecast from the Org level"""

    def __init__(self):
        super().__init__()
        self.__aws_role = self._environment_variables_dict.get("AWS_ACCOUNT_ROLE")
        self.__access_key, self.__secret_key, self.__session = self.__get_sts_credentials()
        self.__ce_client = boto3.client('ce', aws_access_key_id=self.__access_key, aws_secret_access_key=self.__secret_key, aws_session_token=self.__session)
        self.__cost_explorer_operations = CostExplorerOperations(ce_client=self.__ce_client)
        self.__cost_center_owner = literal_eval(self._environment_variables_dict.get('COST_CENTER_OWNER'))

    def __get_sts_credentials(self):
        """This method returns the temporary credentials from the sts service"""
        try:
            sts_client = boto3.client("sts")
            response = sts_client.assume_role(RoleArn=self.__aws_role, RoleSessionName="PayerCostBillingReports")
            credentials = response.get('Credentials')
            return credentials.get('AccessKeyId'), credentials.get('SecretAccessKey'), credentials.get('SessionToken')
        except Exception as err:
            raise err

    def filter_data_by_tag(self, cost_data: dict, tag: str, cost_center: int = ''):
        """
        This method extract data by tag
        @param tag:
        @param cost_data: Data from the cloud explorer
        @param cost_center:
        @return: converted into dict format
        """
        data = {}
        if cost_data.get('ResultsByTime'):
            for results_by_time in cost_data.get('ResultsByTime'):
                start_time = results_by_time.get('TimePeriod').get('Start')
                for group in results_by_time.get('Groups'):
                    name = group.get('Keys')[0].split('$')[-1].strip().replace(' ', '-') if group.get('Keys') else ''
                    amount = group.get('Metrics').get('UnblendedCost').get('Amount') if group.get('Metrics') else ''
                    if name and amount:
                        if name not in data:
                            if cost_center:
                                acc_cost_center, account_budget, years = self.update_to_gsheet.get_cost_center_budget_details(account_id=name, dir_path='/tmp')
                                timestamp = datetime.datetime.strptime(start_time, '%Y-%m-%d')
                                month = datetime.datetime.strftime(timestamp, "%Y %b")
                                owner = self.__cost_center_owner.get(str(acc_cost_center)) if self.__cost_center_owner.get(str(acc_cost_center)) else 'Others'
                                budget = account_budget if start_time.split('-')[0] in years else 0
                                index_id = f'{start_time}-{name}'
                                upload_data = {tag: name, 'Actual': round(float(amount), 3), 'start_date': start_time,
                                               'timestamp': timestamp, 'CloudName': 'AWS Cloud', 'Month': month,
                                               'Forecast': 0,
                                               'filter_date': f'{start_time} {month.split()[-1]}',
                                               'Budget': round(budget / self.MONTHS, 3), 'CostCenter': cost_center,
                                               'AllocatedBudget': budget,
                                               "Owner": owner
                                               }
                            else:
                                index_id = f'{start_time}-{name}'
                                upload_data = {tag: name, 'Actual': round(float(amount), 3)}
                            if index_id:
                                data[index_id] = upload_data
        if cost_data.get('DimensionValueAttributes'):
            for dimension_values in cost_data.get('DimensionValueAttributes'):
                account_id = dimension_values.get("Value")
                account = dimension_values.get('Attributes').get('description')
                for key_index_id in data.keys():
                    if account_id in key_index_id:
                        index_id = f'{data[key_index_id]["start_date"]}-{account}'.lower()
                        data[key_index_id].update({'Account': account, 'index_id': index_id})
        return data

    def filter_forecast_data(self, cost_forecast_data: list, cost_usage_data: dict, account_id: str, cost_center: int, account: str):
        acc_cost_center, account_budget, years = self.update_to_gsheet.get_cost_center_budget_details(account_id=account_id, dir_path='/tmp')
        owner = self.__cost_center_owner.get(str(acc_cost_center)) if self.__cost_center_owner.get(str(acc_cost_center)) else 'Others'
        for cost_forecast in cost_forecast_data:
            start_date = str((cost_forecast.get('TimePeriod').get('Start')))
            start_year = start_date.split('-')[0]
            cost = round(float(cost_forecast.get('MeanValue')), 3)
            index = f'{start_date}-{account_id}'
            if index in cost_usage_data[account]:
                cost_usage_data[account][index]['Forecast'] = cost
            else:
                data = {}
                data['AccountId'] = account_id
                data['Actual'] = 0
                data['Forecast'] = cost
                data['Account'] = account
                data['start_date'] = str((cost_forecast.get('TimePeriod').get('Start')))
                data['index_id'] = f"""{data['start_date']}-{data['Account'].lower()}"""
                data['timestamp'] = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d')
                data['Month'] = datetime.datetime.strftime(data['timestamp'], '%Y %b')
                data['Owner'] = owner
                if start_year in years:
                    data['Budget'] = round(account_budget / self.MONTHS, 3)
                    data['AllocatedBudget'] = account_budget
                else:
                    data['Budget'] = 0
                    data['AllocatedBudget'] = 0
                data['CostCenter'] = cost_center
                data['CloudName'] = "AWS Cloud"
                data['filter_date'] = data['start_date'] + data['Month']
                cost_usage_data[account][index] = data

    @logger_time_stamp
    def get_linked_accounts_forecast(self, linked_account_usage: dict):
        """
        This method append the forecast to the linked accounts
        """
        start_date, end_date = self.get_date_ranges(days=self.FORECAST_DAYS)
        for account, account_cost_usage in copy.deepcopy(linked_account_usage).items():
            list_usage = list(account_cost_usage.values())[0]
            cost_center, account_id = list_usage.get('CostCenter'), list_usage.get('AccountId')
            try:
                cost_forecast_data = self.__cost_explorer_operations.get_cost_forecast(start_date=start_date, end_date=end_date, granularity=self.GRANULARITY, cost_metric=self.COST_METRIC, Filter={'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': [account_id]}})
                self.filter_forecast_data(cost_forecast_data=cost_forecast_data['ForecastResultsByTime'], cost_center=cost_center, account=account, account_id=account_id, cost_usage_data=linked_account_usage)
            except:
                logger.info(f'No Data to get forecast: {account_id}: {account}')

    @logger_time_stamp
    def get_cost_centers(self):
        """
        This method fetch the cost centers from the account
        """
        end_date = datetime.datetime.now() - datetime.timedelta(days=5)
        start_date = end_date - datetime.timedelta(days=1)
        cost_center_data = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"), granularity="MONTHLY", GroupBy=[{'Type': 'COST_CATEGORY', 'Key': 'CostCenter'}])
        return list(self.filter_data_by_tag(cost_center_data, tag='CostCenter').values())

    @logger_time_stamp
    def get_linked_accounts_usage(self):
        """This method get the linked accounts usage using cost center"""
        cost_centers = self.get_cost_centers()
        cost_usage_data = {}
        start_date, end_date = self.get_date_ranges()
        for cost_center in cost_centers:
            cost_data = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity="MONTHLY", GroupBy=[{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}], Filter={'CostCategories': {'Key': 'CostCenter', 'Values': [cost_center.get('CostCenter')]}})
            cost_center_usage_accounts = self.filter_data_by_tag(cost_data, tag='AccountId', cost_center=int(cost_center.get('CostCenter')))
            for idx, usage in cost_center_usage_accounts.items():
                account = usage['Account']
                cost_usage_data.setdefault(account, {}).update({idx: usage})
        self.get_linked_accounts_forecast(linked_account_usage=cost_usage_data)
        self.upload_data_elastic_search(linked_account_usage=cost_usage_data)
        return cost_usage_data

    @logger_time_stamp
    def upload_data_elastic_search(self, linked_account_usage: dict):
        """This method uploads the data to elastic search"""
        for account, monthly_cost in linked_account_usage.items():
            monthly_account_cost = []
            for month, cost in monthly_cost.items():
                monthly_account_cost.append(cost)
            self.elastic_upload.es_upload_data(items=monthly_account_cost, set_index='index_id')

    def run(self):
        """
        This method run the methods
        """
        self.get_linked_accounts_usage()
