import json
import logging
from ast import literal_eval
from datetime import datetime, timedelta

import typeguard

from cloud_governance.cloud_resource_orchestration.utils.constant_variables import DATE_FORMAT
from cloud_governance.cloud_resource_orchestration.utils.elastic_search_queries import ElasticSearchQueries
from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger, handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class CostOverUsage:
    """
    This class monitors the cost explorer reports and sends alert to the user if they exceed specified amount
    """

    DEFAULT_ROUND_DIGITS = 3
    SEND_ALERT_DAY = 3
    FORECAST_GRANULARITY = 'MONTHLY'
    FORECAST_COST_METRIC = 'UNBLENDED_COST'
    OVER_USAGE_THRESHOLD = 0.05
    CLOUD_GOVERNANCE_ES_MAIL_INDEX = 'cloud-governance-mail-messages'
    CRO_OVER_USAGE_ALERT = 'cro-over-usage-alert'
    TIMESTAMP_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__aws_account = self.__environment_variables_dict.get('account', '').replace('OPENSHIFT-', '').strip()
        self.__postfix_mail = Postfix()
        self.__mail_message = MailMessage()
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__over_usage_amount = self.__environment_variables_dict.get('CRO_COST_OVER_USAGE', '')
        self.__es_ce_reports_index = self.__environment_variables_dict.get('USER_COST_INDEX', '')
        self.__ldap_search = LdapSearch(ldap_host_name=self.__environment_variables_dict.get('LDAP_HOST_NAME', ''))
        self.__cro_admins = self.__environment_variables_dict.get('CRO_DEFAULT_ADMINS', [])
        self.es_index_cro = self.__environment_variables_dict.get('CRO_ES_INDEX', '')
        self.__cro_duration_days = self.__environment_variables_dict.get('CRO_DURATION_DAYS')
        self.current_end_date = datetime.utcnow()
        self.current_start_date = self.current_end_date - timedelta(days=self.__cro_duration_days)
        self.__public_cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self.__ce_operations = CostExplorerOperations()
        self.es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self.__over_usage_threshold = self.OVER_USAGE_THRESHOLD * self.__over_usage_amount
        self.__ec2_operations = EC2Operations()
        self.__elastic_search_queries = ElasticSearchQueries(cro_duration_days=self.__cro_duration_days)

    def get_cost_explorer_operations(self):
        return self.__ce_operations

    @typeguard.typechecked
    @logger_time_stamp
    def get_cost_based_on_tag(self, start_date: str, end_date: str, tag_name: str, extra_filters: any = None, extra_operation: str = 'And', granularity: str = None, forecast: bool = False):
        """
        This method gives the cost based on the tag_name
        :param forecast:
        :param granularity:
        :param extra_operation: default, And
        :param extra_filters:
        :param tag_name:
        :param start_date:
        :param end_date:
        :return:
        """
        # remove_savings_cost = {  # removed the savings plan usage from the user costs
        #     'Not': {
        #         'Dimensions': {
        #             'Key': 'RECORD_TYPE',
        #             'Values': ['SavingsPlanRecurringFee', 'SavingsPlanNegation', 'SavingsPlanCoveredUsage']
        #         }
        #     }
        # }
        Filters = {} #remove_savings_cost
        if extra_filters:
            if type(extra_filters) == list:
                if len(extra_filters) == 1:
                    Filters = extra_filters[0]
                else:
                    Filters = {
                        extra_operation: [
                            *extra_filters,
                            # remove_savings_cost
                        ]
                    }
            else:
                Filters = {
                    # extra_operation: [
                        extra_filters
                        # remove_savings_cost
                    # ]
                }
        if forecast:
            results_by_time = self.__ce_operations.get_cost_forecast(start_date=start_date, end_date=end_date, granularity=self.FORECAST_GRANULARITY, cost_metric=self.FORECAST_COST_METRIC, Filter=Filters)['Total']
            response = [{'Forecast': round(float(results_by_time.get('Amount')), self.DEFAULT_ROUND_DIGITS)}]
        else:
            results_by_time = self.__ce_operations.get_cost_by_tags(start_date=start_date, end_date=end_date, tag=tag_name, Filter=Filters, granularity=granularity)['ResultsByTime']
            response = self.__ce_operations.get_filter_data(ce_data=results_by_time, tag_name=tag_name)
        return response

    @typeguard.typechecked
    @logger_time_stamp
    def __get_start_end_dates(self, start_date: datetime = None, end_date: datetime = None):
        """
        This method returns the start_date and end_date
        :param start_date:
        :param end_date:
        :return:
        """
        if not start_date and not end_date:
            end_date = self.current_end_date.date()
            start_date = self.current_start_date.date()
        elif not start_date:
            start_date = self.current_start_date.date()
            end_date = end_date.date()
        else:
            if not end_date:
                end_date = self.current_end_date.date()
            else:
                end_date = end_date.date()
            start_date = start_date.date()
        return start_date, end_date

    @typeguard.typechecked
    @logger_time_stamp
    def get_monthly_user_es_cost_data(self, tag_name: str = 'User', start_date: datetime = None, end_date: datetime = None, extra_matches: any = None, granularity: str = 'MONTHLY', extra_operation: str = 'And'):
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
        return self.get_cost_based_on_tag(start_date=str(start_date), end_date=str(end_date), tag_name=tag_name, granularity=granularity, extra_filters=extra_matches, extra_operation=extra_operation)

    def get_forecast_cost_data(self, tag_name: str = 'User', start_date: datetime = None, end_date: datetime = None, extra_matches: any = None, granularity: str = 'MONTHLY', extra_operation: str = 'And'):
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
        return self.get_cost_based_on_tag(start_date=str(start_date), end_date=str(end_date), tag_name=tag_name, granularity=granularity, extra_filters=extra_matches, extra_operation=extra_operation, forecast=True)

    def get_user_active_ticket_costs(self, user_name: str):
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
                             {"term": {"account_name.keyword": self.__aws_account.upper()}}
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

    def get_user_closed_ticket_costs(self, user_name: str):
        """
        This method returns the users closed tickets costs
        :param user_name:
        :return:
        """
        match_conditions = [{"term": {"user.keyword": user_name}},
                            {"term": {"account_name.keyword": self.__aws_account.upper()}}
                            ]
        query = self.__elastic_search_queries.get_all_closed_tickets(match_conditions=match_conditions)
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

    @logger_time_stamp
    def get_cost_over_usage_users(self):
        """
        This method returns the cost over usage users which are not opened ticket
        :return:
        """
        over_usage_users = []
        current_month_users = self.get_monthly_user_es_cost_data()
        for user in current_month_users:
            user_name = str(user.get('User'))
            user_cost = round(user.get('Cost'), self.DEFAULT_ROUND_DIGITS)
            if user_cost >= (self.__over_usage_amount - self.__over_usage_threshold):
                user_active_tickets_cost = self.get_user_active_ticket_costs(user_name=user_name.lower())
                user_closed_tickets_cost = self.get_user_closed_ticket_costs(user_name=user_name.lower())
                if not user_active_tickets_cost:
                    over_usage_users.append(user)
                else:
                    user_cost_without_active_ticket = user_cost - user_active_tickets_cost - user_closed_tickets_cost
                    if user_cost_without_active_ticket > self.__over_usage_amount:
                        user['Cost'] = user_cost_without_active_ticket
                        over_usage_users.append(user)
        return over_usage_users

    @logger_time_stamp
    def send_alerts_to_over_usage_users(self):
        """
        This method send alerts to cost over usage users
        Send alert to users every 3rd day, if not open ticket
        :return:
        """
        users_list = self.get_cost_over_usage_users()
        alerted_users = []
        for row in users_list:
            user, cost, project = row.get('User'), row.get('Cost'), row.get('Project', '')
            # send_alert, alert_number = self.get_last_mail_alert_status(user=str(user))
            # if send_alert:
            alerted_users.append(user)
            cc = [*self.__cro_admins]
            user_details = self.__ldap_search.get_user_details(user_name=user)
            if user_details:
                if self.__ec2_operations.verify_active_instances(tag_name='User', tag_value=str(user)):
                    name = f'{user_details.get("FullName")}'
                    cc.append(user_details.get('managerId'))
                    subject, body = self.__mail_message.cro_cost_over_usage(CloudName=self.__public_cloud_name,
                                                                            OverUsageCost=self.__over_usage_amount,
                                                                            FullName=name, Cost=cost, Project=project, to=user)
                    es_data = {'Alert': 1, 'MissingUserTicketCost': cost}
                    handler.setLevel(logging.WARN)
                    self.__postfix_mail.send_email_postfix(to=user, cc=[], content=body, subject=subject, mime_type='html', es_data=es_data, message_type=self.CRO_OVER_USAGE_ALERT)
                    handler.setLevel(logging.INFO)
        return alerted_users

    def get_last_mail_alert_status(self, user: str):
        """
        This method return the last mail alert.
        :param user:
        :return:
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"To.keyword": user}},
                        {"term": {"MessageType.keyword": self.CRO_OVER_USAGE_ALERT}},
                    ]
                }
            },
            "size": 1,
            "sort": {"timestamp": "desc"}
        }
        response = self.es_operations.fetch_data_by_es_query(query=query, es_index=self.CLOUD_GOVERNANCE_ES_MAIL_INDEX, search_size=1, limit_to_size=True)
        if response:
            last_alert = response[0]
            last_send_date = last_alert.get('_source').get('timestamp')
            alert_number = last_alert.get('_source').get('Alert', 0)
            current_date = datetime.utcnow().date()
            last_send_date = datetime.strptime(last_send_date, self.TIMESTAMP_DATE_FORMAT).date()
            days = (current_date - last_send_date).days
            if days % self.SEND_ALERT_DAY == 0 and last_send_date != current_date:
                return True, alert_number
            logger.warning(f"Already sent mail on {last_send_date} to {user}")
            return False, alert_number
        return True, 0

    @logger_time_stamp
    def run(self):
        """
        This method runs the cost over usage methods
        :return:
        """
        return self.send_alerts_to_over_usage_users()
