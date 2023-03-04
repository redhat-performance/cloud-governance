import datetime

from dateutil.relativedelta import relativedelta

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
        self.cost_center, self.__account_budget, self.__years, self.__owner = self.update_to_gsheet.get_cost_center_budget_details(account_id=self.__ibm_account.short_account_id)

    def prepare_es_data(self, month: str, year: str, usage_cost: float = 0, next_invoice: float = 0):
        """This method prepares the data to upload to the es"""
        start_date = f'{year}-{month}-01'
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
            'Owner': self.__owner,
            'Forecast': round(next_invoice, 3),
            'Actual': round(usage_cost, 3),
            'filter_date': f'{start_date}-{month.split()[-1]}',
        }
        return es_data

    def get_cost_usage_details(self):
        """This method fetch cost usage details"""
        date = datetime.datetime.now()
        month, year = date.month, date.year
        upload_es_data = {}
        usage_data = self.__ibm_account.get_daily_usage(month=month, year=year)
        if usage_data:
            usage_cost = round(usage_data.get('resources').get('billable_cost'), 3)
            next_invoice = self.__ibm_account.get_next_recurring_invoice()
            es_data = self.prepare_es_data(usage_cost=usage_cost, next_invoice=next_invoice, month=date.strftime("%m"), year=str(year))
            upload_es_data[es_data['index_id']] = es_data
        past_month = date - relativedelta(month=month-1)
        last_month, last_month_year = past_month.strftime("%m"), past_month.year
        past_usage_cost = self.__ibm_account.get_daily_usage(month=int(last_month), year=last_month_year)
        if past_usage_cost:
            es_data = self.prepare_es_data(usage_cost=round(past_usage_cost.get('resources').get('billable_cost'), 3), month=str(last_month), year=str(last_month_year))
            upload_es_data[es_data['index_id']] = es_data
        for next_month in range(self.MONTHS):
            next_month = (next_month + month) % self.MONTHS
            if next_month != month:
                c_year = year
                if len(str(next_month)) != 2:
                    next_month = f'0{next_month}'
                if next_month == '00':
                    year += 1
                    next_month = str(12)
                es_data = self.prepare_es_data(month=str(next_month), year=str(c_year))
                upload_es_data[es_data['index_id']] = es_data
        if upload_es_data:
            self.__elastic_upload.es_upload_data(items=list(upload_es_data.values()), set_index='index_id')
        return list(upload_es_data.values())

    def run(self):
        """This method run the billing methods"""
        self.get_cost_usage_details()
