import logging
from abc import ABC, abstractmethod
from ast import literal_eval
from datetime import datetime, timedelta

import typeguard

from cloud_governance.cloud_resource_orchestration.utils.constant_variables import CRO_OVER_USAGE_ALERT, DATE_FORMAT, \
    OVER_USAGE_THRESHOLD, DEFAULT_ROUND_DIGITS
from cloud_governance.cloud_resource_orchestration.utils.elastic_search_queries import ElasticSearchQueries
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class AbstractCostOverUsage(ABC):

    FORECAST_GRANULARITY = 'MONTHLY'
    FORECAST_COST_METRIC = 'UNBLENDED_COST'

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._public_cloud_name = self._environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self._account = self._environment_variables_dict.get('account', '').replace('OPENSHIFT-', '').strip()
        self._es_host = self._environment_variables_dict.get('es_host', '')
        self._es_port = self._environment_variables_dict.get('es_port', '')
        self._over_usage_amount = self._environment_variables_dict.get('CRO_COST_OVER_USAGE', '')
        self._es_ce_reports_index = self._environment_variables_dict.get('USER_COST_INDEX', '')
        self._ldap_search = LdapSearch(ldap_host_name=self._environment_variables_dict.get('LDAP_HOST_NAME', ''))
        self._cro_admins = self._environment_variables_dict.get('CRO_DEFAULT_ADMINS', [])
        self.es_index_cro = self._environment_variables_dict.get('CRO_ES_INDEX', '')
        self._cro_duration_days = self._environment_variables_dict.get('CRO_DURATION_DAYS')
        self._over_usage_threshold = OVER_USAGE_THRESHOLD * self._over_usage_amount
        self.current_end_date = datetime.utcnow()
        self.current_start_date = self.current_end_date - timedelta(days=self._cro_duration_days)
        self.es_operations = ElasticSearchOperations(es_host=self._es_host, es_port=self._es_port)
        self._elastic_search_queries = ElasticSearchQueries(cro_duration_days=self._cro_duration_days)
        self._postfix_mail = Postfix()
        self._mail_message = MailMessage()

    @typeguard.typechecked
    @logger_time_stamp
    def get_monthly_user_es_cost_data(self, tag_name: str = 'User', start_date: datetime = None,
                                      end_date: datetime = None, extra_matches: any = None,
                                      granularity: str = 'MONTHLY', extra_operation: str = 'And', **kwargs):
        """
        This method gets the user cost from the es-data
        :param tag_name: by default User
        :param start_date:
        :param end_date:
        :param extra_matches:
        :param granularity: by default MONTHLY
        :param extra_operation:
        :return:
        """
        start_date, end_date = self.__get_start_end_dates(start_date=start_date, end_date=end_date)
        return self._get_cost_based_on_tag(start_date=str(start_date), end_date=str(end_date), tag_name=tag_name,
                                           granularity=granularity, extra_filters=extra_matches,
                                           extra_operation=extra_operation, **kwargs)

    def _get_forecast_cost_data(self, tag_name: str = 'User', start_date: datetime = None, end_date: datetime = None,
                               extra_matches: any = None, granularity: str = 'MONTHLY', extra_operation: str = 'And'):
        """
        This method returns the forecast based on inputs
        :param tag_name: by default User
        :param start_date:
        :param end_date:
        :param extra_matches:
        :param granularity: by default MONTHLY
        :param extra_operation:
        :return:
        """
        start_date, end_date = self.__get_start_end_dates(start_date=start_date, end_date=end_date)
        return self._get_cost_based_on_tag(start_date=str(start_date), end_date=str(end_date), tag_name=tag_name,
                                           granularity=granularity, extra_filters=extra_matches,
                                           extra_operation=extra_operation, forecast=True)

    @typeguard.typechecked
    @logger_time_stamp
    def _get_user_active_ticket_costs(self, user_name: str):
        """
        This method returns a boolean indicating whether the user should open the ticket or not
        :param user_name:
        :return:
        """
        query = {  # check user opened the ticket in elastic_search
            "query": {
                "bool": {
                    "must": [{"term": {"user_cro.keyword": user_name}},
                             {"terms": {"ticket_id_state.keyword": ['new', 'manager-approved', 'in-progress']}},
                             {"term": {"account_name.keyword": self._account.upper()}},
                             {"term": {"cloud_name.keyword": self._public_cloud_name.upper()}},
                             ],
                    "filter": {
                        "range": {
                            "timestamp": {
                                "format": "yyyy-MM-dd",
                                "lte": str(self.current_end_date.date()),
                                "gte": str(self.current_start_date.date()),
                            }
                        }
                    }
                }
            }
        }
        user_active_tickets = self.es_operations.fetch_data_by_es_query(es_index=self.es_index_cro, query=query)
        if not user_active_tickets:
            return None
        else:
            total_active_ticket_cost = 0
            for cro_data in user_active_tickets:
                opened_ticket_cost = float(cro_data.get('_source').get('estimated_cost'))
                total_active_ticket_cost += opened_ticket_cost
            return total_active_ticket_cost

    @typeguard.typechecked
    @logger_time_stamp
    def _get_user_closed_ticket_costs(self, user_name: str):
        """
        This method returns the users closed tickets cost
        :param user_name:
        :type user_name:
        :return:
        :rtype:
        """
        match_conditions = [{"term": {"user.keyword": user_name}},
                            {"term": {"account_name.keyword": self._account.upper()}},
                            {"term": {"cloud_name.keyword": self._public_cloud_name}}
                            ]
        query = self._elastic_search_queries.get_all_closed_tickets(match_conditions=match_conditions)
        user_closed_tickets = self.es_operations.fetch_data_by_es_query(es_index=self.es_index_cro, query=query,
                                                                        filter_path='hits.hits._source')
        total_closed_ticket_cost = 0
        for closed_ticket in user_closed_tickets:
            total_used_cost = 0
            user_daily_report = closed_ticket.get('_source', {}).get('user_daily_cost', '')
            if user_daily_report:
                user_daily_report = literal_eval(user_daily_report)
                for date, user_cost in user_daily_report.items():
                    if datetime.strptime(date, DATE_FORMAT) >= self.current_start_date:
                        total_used_cost += int(user_cost.get('TicketId', 0))
            total_closed_ticket_cost += total_used_cost
        return total_closed_ticket_cost

    @typeguard.typechecked
    @logger_time_stamp
    def __get_start_end_dates(self, start_date: datetime = None, end_date: datetime = None):
        """
        This method returns the start_date and end_date
        :param start_date:
        :param end_date:
        :return:
        """
        if not start_date:
            start_date = self.current_start_date
        if not end_date:
            end_date = self.current_end_date
        return start_date.date(), end_date.date()

    @logger_time_stamp
    def _get_cost_over_usage_users(self):
        """
        This method returns the cost over usage users which are not opened ticket
        :return:
        """
        over_usage_users = []
        current_month_users = self.get_monthly_user_es_cost_data()
        for user in current_month_users:
            user_name = str(user.get('User'))
            user_cost = round(user.get('Cost'), DEFAULT_ROUND_DIGITS)
            if user_cost >= (self._over_usage_amount - self._over_usage_threshold):
                user_active_tickets_cost = self._get_user_active_ticket_costs(user_name=user_name.lower())
                user_closed_tickets_cost = self._get_user_closed_ticket_costs(user_name=user_name.lower())
                if not user_active_tickets_cost:
                    over_usage_users.append(user)
                else:
                    user_cost_without_active_ticket = user_cost - user_active_tickets_cost - user_closed_tickets_cost
                    if user_cost_without_active_ticket > self._over_usage_amount:
                        user['Cost'] = user_cost_without_active_ticket
                        over_usage_users.append(user)
        return over_usage_users

    @logger_time_stamp
    def _send_alerts_to_over_usage_users(self):
        users_list = self._get_cost_over_usage_users()
        alerted_users = []
        for row in users_list:
            user, cost, project = row.get('User'), row.get('Cost'), row.get('Project', '')
            alerted_users.append(user)
            cc = [*self._cro_admins]
            user_details = self._ldap_search.get_user_details(user_name=user)
            if user_details:
                if self._verify_active_resources(tag_name='User', tag_value=str(user)):
                    name = f'{user_details.get("FullName")}'
                    cc.append(user_details.get('managerId'))
                    subject, body = self._mail_message.cro_cost_over_usage(CloudName=self._public_cloud_name,
                                                                           OverUsageCost=self._over_usage_amount,
                                                                           FullName=name, Cost=cost, Project=project,
                                                                           to=user)
                    es_data = {'Alert': 1, 'MissingUserTicketCost': cost, 'Cloud': self._public_cloud_name}
                    handler.setLevel(logging.WARN)
                    self._postfix_mail.send_email_postfix(to=user, cc=[], content=body, subject=subject,
                                                          mime_type='html', es_data=es_data,
                                                          message_type=CRO_OVER_USAGE_ALERT)
                    handler.setLevel(logging.INFO)
        return alerted_users

    @logger_time_stamp
    def run(self):
        """
        This method runs the cost over usage alerts to users
        :return:
        :rtype:
        """
        return self._send_alerts_to_over_usage_users()

    @abstractmethod
    def _verify_active_resources(self, tag_name: str, tag_value: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _get_cost_based_on_tag(self, start_date: str, end_date: str, tag_name: str, extra_filters: any = None,
                               extra_operation: str = 'And', granularity: str = None, forecast: bool = False, **kwargs):
        raise NotImplementedError
