import datetime
import json

from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.google_drive.gcp_operations import GCPOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.common.utils.configs import LOOK_BACK_DAYS, IT_ACCOUNTS_COST_REPORTS_LIST, MONTHS, \
    DEFAULT_ROUND_DIGITS, DATE_FORMAT
from cloud_governance.common.utils.utils import Utils
from cloud_governance.main.environment_variables import environment_variables


class CloudabilityCostReports:
    """
    This class performs cloudability cost operations
    """

    APPITO_LOGIN_API = "https://frontdoor.apptio.com/service/apikeylogin"

    def __init__(self):
        self.__api_requests = APIRequests()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__view_id = self.__environment_variables_dict.get('CLOUDABILITY_VIEW_ID')
        self.__dimensions = self.__environment_variables_dict.get('CLOUDABILITY_DIMENSIONS')
        self.__metrics = self.__environment_variables_dict.get('CLOUDABILITY_METRICS')
        self.__cloudability_api = self.__environment_variables_dict.get('CLOUDABILITY_API')
        self.__reports_path = self.__environment_variables_dict.get('CLOUDABILITY_API_REPORTS_PATH')
        self.__appito_envid = self.__environment_variables_dict.get('APPITO_ENVID')
        self.__key_secret = self.__environment_variables_dict.get('APPITO_KEY_SECRET')
        self.__key_access = self.__environment_variables_dict.get('APPITO_KEY_ACCESS')
        self.__gcp_operations = GCPOperations()
        self.elastic_upload = ElasticUpload()

    def __get_appito_token(self):
        """
        This method returns the appito token
        :return:
        :rtype:
        """
        data = {
            "keyAccess": self.__key_access,
            "keySecret": self.__key_secret
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = self.__api_requests.post(url=self.APPITO_LOGIN_API, data=json.dumps(data), headers=headers)
        if response.ok:
            return response.headers['apptio-opentoken']
        return None

    def __get_start_date(self):
        return (self.__get_end_date() - datetime.timedelta(days=LOOK_BACK_DAYS)).replace(day=1)

    def __get_end_date(self):
        return datetime.datetime.utcnow().date()

    def __get_cost_reports(self, start_date: str = None, end_date: str = None, custom_filter: str = ''):
        """
        This method returns the cost reports from the cloudability
        :return:
        :rtype:
        """
        appito_token = self.__get_appito_token()
        if not appito_token:
            raise Exception("Appito Token missing error")
        if not start_date:
            start_date = self.__get_start_date()
        if not end_date:
            end_date = self.__get_end_date()
        api = (f'{self.__cloudability_api}/{self.__reports_path}?'
               f'dimensions={self.__dimensions}&metrics={self.__metrics}'
               f'&start_date={start_date}&end_date={end_date}'
               f'&id={self.__view_id}&{custom_filter}')
        headers = {
            "apptio-environmentid": self.__appito_envid,
            "apptio-opentoken": appito_token
        }

        response = self.__api_requests.get(url=api, headers=headers)
        if isinstance(response, dict):
            return response.get('results')
        return {}

    def __get_analysed_reports(self):
        """
        This method returns the cost reports by adding actual usage, allocated budget
        :return:
        :rtype:
        """
        accounts_reports_df = self.__gcp_operations.get_accounts_sheet(sheet_name=IT_ACCOUNTS_COST_REPORTS_LIST)
        cost_centers = list(set(accounts_reports_df['CostCenter'].tolist()))
        custom_filter = '&'.join([f'filters=category4=={cost_center}' for cost_center in cost_centers])
        cloudability_reports = self.__get_cost_reports(custom_filter=custom_filter)
        cost_reports = {}
        for account in cloudability_reports:
            account['date'] = (datetime.datetime.strptime(account.get('date', ''), DATE_FORMAT)
                               .replace(day=1).date().__str__())
            account_id = account.get('vendor_account_identifier').replace('-', '')
            account_row = accounts_reports_df[accounts_reports_df['AccountId'] == account_id].reset_index().to_dict(
                orient='records')
            if account_row:
                timestamp = datetime.datetime.strptime(account.get('date'), '%Y-%m-%d')
                account_data = account_row[0]
                cost_center = account_data.get('CostCenter', 0)
                account_budget = round(float(account_data.get('Budget', '0').replace(',', '')))
                year = str(account_data.get('Year'))
                account_owner = account_data.get('Owner')
                cloud_name = account.get('vendor').upper()
                if Utils.equal_ignore_case(cloud_name, 'amazon'):
                    cloud_name = 'AWS'
                month = datetime.datetime.strftime(timestamp, '%Y %b')
                index_id = f"""cloudability-{account.get('date')}-{account.get('vendor_account_name').lower()}"""

                if year in account.get('date'):
                    if index_id not in cost_reports:
                        cost_reports.setdefault(index_id, {}).update({
                            'Account': account.get('vendor_account_name'),
                            'Actual': round(float(account.get('unblended_cost')), DEFAULT_ROUND_DIGITS),
                            'AccountId': account_id,
                            'Owner': account_owner,
                            'start_date': account.get('date'),
                            'CloudName': cloud_name,
                            'Forecast': 0,
                            'index_id': index_id,
                            'timestamp': timestamp,
                            'Month': month,
                            'Budget': round(account_budget / MONTHS, DEFAULT_ROUND_DIGITS),
                            'AllocatedBudget': account_budget,
                            'CostCenter': cost_center,
                            'filter_date': f'{account.get("date")}-{month.split()[-1]}'
                        })
                    else:
                        cost_reports[index_id]['Actual'] += round(float(account.get('unblended_cost')), DEFAULT_ROUND_DIGITS)
        return list(cost_reports.values())

    def __next_twelve_months(self):
        """
        This method returns the next 12 months, year
        :return:
        """
        year = datetime.datetime.utcnow().year
        next_month = datetime.datetime.utcnow().month + 1
        month_year = []
        for idx in range(MONTHS):
            month = str((idx + next_month) % MONTHS)
            c_year = year
            if len(month) == 1:
                month = f'0{month}'
            if month == '00':
                month = 12
                year = year+1
            month_year.append((str(month), c_year))
        return month_year

    def __forecast_for_next_months(self, cost_data: list):
        """
        This method returns the forecast of next twelve months data
        :param cost_data:
        :return:
        """
        forecast_cost_data = []
        month_years = self.__next_twelve_months()
        month = (datetime.datetime.utcnow().month - 1) % 12
        if month == 0:
            month = 12
        if len(str(month)) == 1:
            month = f'0{month}'
        year = datetime.datetime.utcnow().year
        cache_start_date = f'{year}-{str(month)}-01'
        for data in cost_data:
            if cache_start_date == data.get('start_date') and data.get('CostCenter') > 0:
                for m_y in month_years:
                    m, y = m_y[0], m_y[1]
                    start_date = f'{y}-{m}-01'
                    timestamp = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    index_id = f'cloudability-{start_date}-{data.get("Account").lower()}'
                    month = datetime.datetime.strftime(timestamp, "%Y %b")
                    forecast_cost_data.append({
                        **data,
                        'Actual': 0,
                        'start_date': start_date,
                        'timestamp': timestamp,
                        'index_id': index_id,
                        'filter_date': f'{start_date}-{month.split()[-1]}',
                        'Month': month}
                    )
        return forecast_cost_data

    def __get_cost_and_upload(self):
        """
        This method collect the cost and uploads to the ElasticSearch
        :return:
        """
        collected_data = self.__get_analysed_reports()
        forecast_data = self.__forecast_for_next_months(cost_data=collected_data)
        upload_data = collected_data + forecast_data
        self.elastic_upload.es_upload_data(items=upload_data, set_index='index_id')
        return upload_data

    def run(self):
        """
        This is the starting of the operations
        :return:
        :rtype:
        """
        logger.info(f'Cloudability Cost Reports=> ReportsPath: {self.__reports_path}, Metrics: {self.__metrics}, API: {self.__cloudability_api}')
        self.__get_cost_and_upload()
