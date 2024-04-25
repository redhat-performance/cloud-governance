import copy
import datetime
import logging
from ast import literal_eval

import boto3

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.savingsplan.savings_plans_operations import SavingsPlansOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.logger.init_logger import logger, handler
from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.policy.aws.cost_billing_reports import CostBillingReports


class CostExplorerPayerBillings(CostBillingReports):
    """
    This class is responsible for generation cost billing report for Budget, Actual, Forecast from the Org level
    Monthly savings Plan Amortization: (linked_account_total_cost/payer_account_total_cost) * monthly_savings_plan_cost
    Monthly_support_fee: (monthly_support_fee - (monthly_support_fee * discount ) ) * (linked_account_total_cost/payer_account_total_cost)
    """

    DEFAULT_ROUND_DIGITS = 3

    def __init__(self):
        super().__init__()
        self.__savings_plan_list = None
        self.__aws_role = self._environment_variables_dict.get("AWS_ACCOUNT_ROLE")
        self.__access_key, self.__secret_key, self.__session = self.__get_sts_credentials()
        self.__ce_client = boto3.client('ce', aws_access_key_id=self.__access_key, aws_secret_access_key=self.__secret_key, aws_session_token=self.__session)
        self.__savings_plan_client = boto3.client('savingsplans', aws_access_key_id=self.__access_key, aws_secret_access_key=self.__secret_key, aws_session_token=self.__session)
        self.__iam_client = boto3.client('iam', aws_access_key_id=self.__access_key, aws_secret_access_key=self.__secret_key, aws_session_token=self.__session)
        self.__assumed_role_account_name = IAMOperations(iam_client=self.__iam_client).get_account_alias_cloud_name()
        self.__cost_explorer_operations = CostExplorerOperations(ce_client=self.__ce_client)
        self.__savings_plan_operations = SavingsPlansOperations(savings_plan_client=self.__savings_plan_client)
        self.__replacement_account = literal_eval(self._environment_variables_dict.get('REPLACE_ACCOUNT_NAME'))
        self.__savings_discounts = float(self._environment_variables_dict.get('PAYER_SUPPORT_FEE_CREDIT', 0))
        self.__monthly_cost_for_spa_calc = {}
        self.__monthly_cost_for_support_fee = {}
        self.__temporary_dir = self._environment_variables_dict.get('TEMPORARY_DIR', '')

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
                                acc_cost_center, account_budget, years, owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=name, dir_path=self.__temporary_dir)
                                timestamp = datetime.datetime.strptime(start_time, '%Y-%m-%d')
                                month = datetime.datetime.strftime(timestamp, "%Y %b")
                                month_full_name = datetime.datetime.strftime(timestamp, "%B")
                                payer_monthly_savings_plan = self.__savings_plan_list[start_time]
                                budget = account_budget if start_time.split('-')[0] in years else 0
                                index_id = f'{start_time}-{name}'
                                upload_data = {tag: name, 'Actual': round(float(amount), self.DEFAULT_ROUND_DIGITS), 'start_date': start_time,
                                               'timestamp': timestamp, 'CloudName': 'AWS', 'Month': month,
                                               'Forecast': 0,
                                               'filter_date': f'{start_time}-{month.split()[-1]}',
                                               'Budget': round(budget / self.MONTHS, self.DEFAULT_ROUND_DIGITS), 'CostCenter': cost_center,
                                               'AllocatedBudget': budget,
                                               "Owner": owner,
                                               'AmortizedSavingsPlan': payer_monthly_savings_plan,
                                               'SavingsPlanCost': (float(amount) / float(self.__monthly_cost_for_spa_calc.get(start_time))) * payer_monthly_savings_plan,
                                               'TotalPercentage': (float(amount) / float(self.__monthly_cost_for_spa_calc.get(start_time)))
                                               }
                                upload_data['PremiumSupportFee'] = (float(self.__monthly_cost_for_support_fee.get(start_time)) - (float(self.__monthly_cost_for_support_fee.get(start_time)) * self.__savings_discounts)) * upload_data['TotalPercentage'],
                            else:
                                index_id = f'{start_time}-{name}'
                                upload_data = {tag: name, 'Actual': round(float(amount), self.DEFAULT_ROUND_DIGITS)}
                            if index_id:
                                data[index_id] = upload_data
        if cost_data.get('DimensionValueAttributes'):
            for dimension_values in cost_data.get('DimensionValueAttributes'):
                account_id = dimension_values.get("Value")
                account = dimension_values.get('Attributes').get('description')
                if self.__replacement_account.get(account):
                    account = self.__replacement_account.get(account)
                for key_index_id in data.keys():
                    if account_id in key_index_id:
                        index_id = f'{data[key_index_id]["start_date"]}-{account}'.lower()
                        data[key_index_id].update({'Account': account, 'index_id': index_id})
        return data

    def filter_forecast_data(self, cost_forecast_data: list, cost_usage_data: dict, account_id: str, cost_center: int, account: str):
        acc_cost_center, account_budget, years, owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=account_id, dir_path=self.__temporary_dir)
        for cost_forecast in cost_forecast_data:
            start_date = str((cost_forecast.get('TimePeriod').get('Start')))
            start_year = start_date.split('-')[0]
            cost = round(float(cost_forecast.get('MeanValue')), self.DEFAULT_ROUND_DIGITS)
            index = f'{start_date}-{account_id}'
            month_full_name = datetime.datetime.strftime(datetime.datetime.strptime(start_date, '%Y-%m-%d'), "%B")
            total_percentage = (cost / float(self.__monthly_cost_for_spa_calc.get(start_date)))
            payer_monthly_savings_plan = self.__savings_plan_list[start_date]
            if index in cost_usage_data[account]:
                cost_usage_data[account][index]['Forecast'] = cost
                cost_usage_data[account][index]['TotalPercentage'] = total_percentage
                cost_usage_data[account][index]['SavingsPlanCost'] = total_percentage * payer_monthly_savings_plan
                cost_usage_data[account][index]['PremiumSupportFee'] = total_percentage * (float(self.__monthly_cost_for_support_fee.get(start_date)) - (float(self.__monthly_cost_for_support_fee.get(start_date)) * self.__savings_discounts))
            else:
                data = {}
                data['AccountId'] = account_id
                data['Actual'] = 0
                data['Forecast'] = cost
                data['TotalPercentage'] = total_percentage
                data['AmortizedSavingsPlan'] = payer_monthly_savings_plan
                data['SavingsPlanCost'] = total_percentage * payer_monthly_savings_plan
                data['PremiumSupportFee'] = total_percentage * (float(self.__monthly_cost_for_support_fee.get(start_date)) - (float(self.__monthly_cost_for_support_fee.get(start_date)) * self.__savings_discounts))
                data['Account'] = account
                data['start_date'] = str((cost_forecast.get('TimePeriod').get('Start')))
                data['index_id'] = f"""{data['start_date']}-{data['Account'].lower()}"""
                data['timestamp'] = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d')
                data['Month'] = datetime.datetime.strftime(data['timestamp'], '%Y %b')
                data['Owner'] = owner
                if start_year in years:
                    data['Budget'] = round(account_budget / self.MONTHS, self.DEFAULT_ROUND_DIGITS)
                    data['AllocatedBudget'] = account_budget
                else:
                    data['Budget'] = 0
                    data['AllocatedBudget'] = 0
                data['CostCenter'] = cost_center
                data['CloudName'] = "AWS"
                data['filter_date'] = f'{data["start_date"]}-{data["Month"].split()[-1]}'
                cost_usage_data[account][index] = data

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
            except Exception as err:
                logger.info(f'No Data to get forecast: {account_id}: {account}, {err}')

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
        self.__savings_plan_list = self.__savings_plan_operations.get_monthly_active_savings_plan_summary()
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
        self.__get_ce_cost_usage_by_filter_tag(tag_name='spot', cost_centers=cost_centers, cost_usage_data=cost_usage_data)
        handler.setLevel(logging.WARN)
        #  To prevent printing the **kwargs of the function when using the logger_time_stamp decorator.
        self.upload_data_elastic_search(linked_account_usage=cost_usage_data)
        handler.setLevel(logging.INFO)
        return cost_usage_data

    def __get_ce_cost_usage_by_filter_tag(self, cost_centers: list, tag_name: str, cost_usage_data: dict):
        """
        This method returns the cost by filter tag_name
        :param cost_centers:
        :param tag_name:
        :return:
        """
        start_date, end_date = self.get_date_ranges()
        for cost_center in cost_centers:
            cost_center_number = cost_center.get('CostCenter')
            filter_cost_center = {'CostCategories': {'Key': 'CostCenter', 'Values': [cost_center_number]}}
            values = self.__cost_explorer_operations.CE_COST_FILTERS[tag_name.upper()]['Values']
            filter_tag_value = {'Dimensions': {'Key': 'PURCHASE_TYPE', 'Values': values}}
            group_by = {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}
            cost_data = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=start_date, end_date=end_date, granularity="MONTHLY",
                                                                                    GroupBy=[group_by], Filter={'And': [filter_cost_center, filter_tag_value]})
            filtered_data = self.__cost_explorer_operations.get_ce_report_filter_data(ce_response=cost_data, tag_name=tag_name)
            if filtered_data:
                for index_id, row in filtered_data.items():
                    account = row.get('Account')
                    if account in self.__replacement_account:
                        account = self.__replacement_account[account]
                    if account in cost_usage_data:
                        cost_usage_data[account][index_id][f'{tag_name.title()}Usage'] = round(float(row.get(tag_name)), self.DEFAULT_ROUND_DIGITS)

    @logger_time_stamp
    def upload_data_elastic_search(self, linked_account_usage: dict):
        """This method uploads the data to elastic search"""
        for account, monthly_cost in linked_account_usage.items():
            monthly_account_cost = []
            for month, cost in monthly_cost.items():
                monthly_account_cost.append(cost)
            self.elastic_upload.es_upload_data(items=monthly_account_cost, set_index='index_id')

    def filter_cost_details_for_sp(self, total_cost: list):
        """"This method filter the account total cost"""
        results = {}
        for row in total_cost:
            start_time = row.get('TimePeriod').get('Start')
            if row.get('MeanValue'):
                cost = round(float(row.get('MeanValue')), self.DEFAULT_ROUND_DIGITS)
            else:
                cost = round(float(row.get('Total').get('UnblendedCost').get('Amount')), self.DEFAULT_ROUND_DIGITS)
            results[start_time] = cost
        return results

    def get_monthly_cost_details(self, start_date: datetime = None, end_date: datetime = None):
        """This method list the savings plan details"""
        current_date = datetime.datetime.utcnow()
        if not start_date and not end_date:
            end_date = (current_date.replace(day=1) - datetime.timedelta(days=1)).date()
            start_date = end_date.replace(day=1)
            end_date = end_date + datetime.timedelta(days=1)
        payer_cost_response = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=str(start_date), end_date=str(end_date), granularity='MONTHLY', cost_metric=self.COST_METRIC, Filter={'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Support', 'Refund', 'Credit']}}})
        payer_support_fee = self.__cost_explorer_operations.get_cost_and_usage_from_aws(start_date=str(start_date), end_date=str(end_date), granularity='MONTHLY', cost_metric=self.COST_METRIC, Filter={'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Support']}})
        filtered_payer_cost = self.filter_cost_details_for_sp(payer_cost_response.get('ResultsByTime'))
        filtered_support_fee = self.filter_cost_details_for_sp(payer_support_fee.get('ResultsByTime'))
        self.__monthly_cost_for_spa_calc = filtered_payer_cost
        self.__monthly_cost_for_support_fee.update(filtered_support_fee)
        start_date = current_date.date()
        end_date = start_date + datetime.timedelta(days=360)
        forecast_response = self.__cost_explorer_operations.get_cost_forecast(start_date=str(start_date), end_date=str(end_date), granularity=self.GRANULARITY, cost_metric=self.COST_METRIC, Filter={'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Support', 'Refund', 'Credit']}}})
        payer_forecast_support_fee = self.__cost_explorer_operations.get_cost_forecast(start_date=str(start_date), end_date=str(end_date), granularity=self.GRANULARITY, cost_metric=self.COST_METRIC, Filter={'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Support']}})
        filtered_payer_forecast = self.filter_cost_details_for_sp(forecast_response.get('ForecastResultsByTime'))
        filtered_payer_support_forecast = self.filter_cost_details_for_sp(payer_forecast_support_fee.get('ForecastResultsByTime'))
        self.__monthly_cost_for_spa_calc.update(filtered_payer_forecast)
        self.__monthly_cost_for_support_fee.update(filtered_payer_support_forecast)

    def run(self):
        """
        This method run the methods
        """
        self.get_monthly_cost_details()
        self.get_linked_accounts_usage()
