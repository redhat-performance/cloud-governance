import datetime

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.google_drive.upload_to_gsheet import UploadToGsheet

from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.main.environment_variables import environment_variables


class CostBillingReports:
    """
    This class is responsible for generation cost billing report for Budget, Actual, Forecast
    """

    MONTHS = 12

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__ibm_account = IBMAccount()
        self.__elastic_upload = ElasticUpload()
        self.update_to_gsheet = UploadToGsheet()
        self.owner = self.__environment_variables_dict.get('COST_CENTER_OWNER')
        self.cost_center, self.__account_budget, self.__years = self.update_to_gsheet.get_cost_center_budget_details(account_id=self.__ibm_account.short_account_id)

    @logger_time_stamp
    def prepare_es_data(self, usage_cost: float, next_invoice: float):
        """This method prepares the data to upload to the es"""
        date = datetime.datetime.now()
        start_date = f'{date.year}-{date.strftime("%m")}-01'
        timestamp = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        month = datetime.datetime.strftime(timestamp, '%Y %b')
        es_data = {
            'AccountId': self.__ibm_account.short_account_id,
            'Account': self.__ibm_account.account.lower(),
            'start_date': timestamp,
            'index_id': f'{start_date}-{self.__ibm_account.short_account_id}',
            'timestamp': timestamp,
            'Budget': round(self.__account_budget/self.MONTHS, 3),
            'AllocatedBudget': self.__account_budget,
            'Month': month,
            'CostCenter': self.cost_center,
            'CloudName': 'IBM Cloud',
            'Owner': self.owner,
            'Forecast': round(next_invoice, 3),
            'Actual': round(usage_cost, 3),
            'filter_date': f'{start_date}-{month.split()[-1]}',
        }
        return es_data

    @logger_time_stamp
    def get_cost_usage_details(self):
        """This method fetch cost usage details"""
        date = datetime.datetime.now()
        month, year = date.month, date.year
        es_data = {}
        usage_data = self.__ibm_account.get_daily_usage(month=month, year=year)
        if usage_data:
            usage_cost = round(usage_data.get('resources').get('billable_cost'), 3)
            next_invoice = self.__ibm_account.get_next_recurring_invoice()
            es_data = self.prepare_es_data(usage_cost=usage_cost, next_invoice=next_invoice)
            self.__elastic_upload.es_upload_data(items=[es_data], set_index='index_id')
        return es_data

    def run(self):
        """This method run the billing methods"""
        self.get_cost_usage_details()
