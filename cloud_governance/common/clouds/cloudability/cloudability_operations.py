import json

from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.common.utils.configs import LOOK_BACK_DAYS
from cloud_governance.main.environment_variables import environment_variables
from datetime import datetime, timedelta, timezone


class CloudabilityOperations:
    APPITO_LOGIN_API = "https://frontdoor.apptio.com/service/apikeylogin"

    def __init__(self):
        self.__api_requests = APIRequests()
        self.environment_variables_dict = environment_variables.environment_variables_dict
        self.__view_id = self.environment_variables_dict.get('CLOUDABILITY_VIEW_ID')
        self.__cloudability_api = self.environment_variables_dict.get('CLOUDABILITY_API')
        self.__reports_path = self.environment_variables_dict.get('CLOUDABILITY_API_REPORTS_PATH')
        self.__appito_envid = self.environment_variables_dict.get('APPITO_ENVID')
        self.__key_secret = self.environment_variables_dict.get('APPITO_KEY_SECRET')
        self.__key_access = self.environment_variables_dict.get('APPITO_KEY_ACCESS')
        self.dimensions = self.environment_variables_dict.get('CLOUDABILITY_DIMENSIONS')
        self.metrics = self.environment_variables_dict.get('CLOUDABILITY_METRICS')

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

    def __get_start_date(self, look_back_days: int = LOOK_BACK_DAYS):
        return (self.__get_end_date() - timedelta(days=look_back_days)).replace(day=1)

    def __get_end_date(self):
        return datetime.now(timezone.utc).date()

    def get_cost_reports(self,
                         dimensions: str = None,
                         metrics: str = None,
                         start_date: str = None,
                         end_date: str = None,
                         custom_filter: str = '',
                         look_back_days: int = LOOK_BACK_DAYS,
                         page_token: str = None):
        """
        This method returns the cost reports from the cloudability
        :return:
        :rtype:
        """
        cost_usage_result = []
        appito_token = self.__get_appito_token()
        if not appito_token:
            raise Exception("Appito Token missing error")

        dimensions = dimensions or self.dimensions
        metrics = metrics or self.metrics
        start_date = start_date or self.__get_start_date(look_back_days)
        end_date = end_date or self.__get_end_date()
        api = f'{self.__cloudability_api}/{self.__reports_path}?' \
              f'dimensions={dimensions}&metrics={metrics}' \
              f'&start_date={start_date}&end_date={end_date}' \
              f'&id={self.__view_id}&{custom_filter}'
        if page_token:
            api += f'&token={page_token}'
        headers = {
            "apptio-environmentid": self.__appito_envid,
            "apptio-opentoken": appito_token
        }
        response = self.__api_requests.get(url=api, headers=headers)
        if isinstance(response, dict):
            results = response.get('results') if response.get('results') else response
            cost_usage_result.extend(results)
            page_token = response.get('pagination', {}).get('next')
            if page_token:
                cost_usage_result.extend(self.get_cost_reports(page_token=page_token,
                                                               dimensions=dimensions,
                                                               metrics=metrics,
                                                               start_date=start_date,
                                                               end_date=end_date,
                                                               custom_filter=custom_filter
                                                               ))

        return cost_usage_result
