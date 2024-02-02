from abc import abstractmethod, ABC
from datetime import datetime

import typeguard

from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.cloud_resource_orchestration.utils.elastic_search_queries import ElasticSearchQueries
from cloud_governance.cloud_resource_orchestration.utils.constant_variables import FIRST_CRO_ALERT, SECOND_CRO_ALERT, \
    CLOSE_JIRA_TICKET, JIRA_ISSUE_NEW_STATE, DATE_FORMAT
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class AbstractMonitorTickets(ABC):
    """
    This Abstract class perform the operations for monitoring tickets
    """

    def __init__(self):
        super().__init__()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_operations = ElasticSearchOperations()
        self.__es_index_cro = self.__environment_variables_dict.get('CRO_ES_INDEX', '')
        self.__account_name = self.__environment_variables_dict.get('account')
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self.__ticket_over_usage_limit = self.__environment_variables_dict.get('TICKET_OVER_USAGE_LIMIT')
        self.__default_admins = self.__environment_variables_dict.get('CRO_DEFAULT_ADMINS', [])
        self.__elasticsearch_queries = ElasticSearchQueries()
        self.__jira_operations = JiraOperations()
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()

    def _get_all_in_progress_tickets(self, account_name: str = '', cloud_name: str = '', fields: list = None):
        """
        This method returns all in-progress tickets
        :param account_name:
        :param cloud_name:
        :param fields:
        :return:
        """
        account_name = account_name if account_name else self.__account_name
        cloud_name = cloud_name if cloud_name else self.__cloud_name
        match_conditions = [
            {"term": {"account_name.keyword": account_name}},
            {"term": {"cloud_name.keyword": cloud_name}}
        ]
        in_progress_tickets_query = self.__elasticsearch_queries.get_all_in_progress_tickets(
            match_conditions=match_conditions, fields=fields)
        in_progress_tickets_list = self.__es_operations.fetch_data_by_es_query(query=in_progress_tickets_query,
                                                                               es_index=self.__es_index_cro, filter_path='hits.hits._source')
        return in_progress_tickets_list

    @abstractmethod
    def update_budget_tag_to_resources(self, region_name: str, ticket_id: str, updated_budget: int):
        """
        This method updates the budget to cloud resources
        :param region_name:
        :param ticket_id:
        :param updated_budget:
        :return:
        """
        raise NotImplemented("This method is not implemented")

    @abstractmethod
    def update_duration_tag_to_resources(self, region_name: str, ticket_id: str, updated_duration: int):
        """
        This method updates the budget to cloud resources
        :param region_name:
        :param ticket_id:
        :param updated_duration:
        :return:
        """
        raise NotImplemented("This method is not implemented")

    @abstractmethod
    def update_cluster_cost(self):
        """
        This method updates the cluster cost.
        :return:
        :rtype:
        """
        raise NotImplemented("This method is not implemented")

    @logger_time_stamp
    def extend_tickets_budget(self, ticket_id: str, region_name: str, current_budget: int = 0):
        """
        This method extends the ticket budget if any
        :param ticket_id:
        :param region_name:
        :param current_budget:
        :return:
        """
        ticket_extended = False
        sub_ticket_ids = self.__jira_operations.get_budget_extend_tickets(ticket_id=ticket_id, ticket_state='inprogress')
        if sub_ticket_ids:
            total_budget_to_extend = self.__jira_operations.get_total_extend_budget(sub_ticket_ids=sub_ticket_ids)
            if string_equal_ignore_case(self.__cloud_name, 'AWS'):
                self.update_budget_tag_to_resources(region_name=region_name, ticket_id=ticket_id,
                                                    updated_budget=total_budget_to_extend)
                update_data = {'estimated_cost': int(current_budget) + int(total_budget_to_extend)}
                self.__es_operations.update_elasticsearch_index(index=self.__es_index_cro, metadata=update_data,
                                                                id=ticket_id)
                for sub_ticket_id in sub_ticket_ids:
                    self.__jira_operations.move_issue_state(ticket_id=sub_ticket_id, state='closed')
                logger.info(f'Updated the budget of the ticket: {ticket_id}')
                ticket_extended = True
        else:
            logger.info(f'No extended tickets for the TicketId: {ticket_id}')
        return ticket_extended

    @typeguard.typechecked
    @logger_time_stamp
    def extend_ticket_duration(self, ticket_id: str, region_name: str, current_duration: int = 0):
        """
        This method extends the duration of the ticket if any
        :param ticket_id:
        :param region_name:
        :return:
        """
        tickets_found = False
        sub_ticket_ids = self.__jira_operations.get_duration_extend_tickets(ticket_id=ticket_id, ticket_state='new')
        if sub_ticket_ids:
            total_duration_to_extend = self.__jira_operations.get_total_extend_duration(sub_ticket_ids=sub_ticket_ids)
            if string_equal_ignore_case(self.__cloud_name, 'AWS'):
                self.update_duration_tag_to_resources(region_name=region_name, ticket_id=ticket_id,
                                                      updated_duration=total_duration_to_extend)
                update_data = {'duration': int(current_duration) + int(total_duration_to_extend)}
                self.__es_operations.update_elasticsearch_index(index=self.__es_index_cro, metadata=update_data,
                                                                id=ticket_id)
                for sub_ticket_id in sub_ticket_ids:
                    self.__jira_operations.move_issue_state(ticket_id=sub_ticket_id, state='closed')
                logger.info(f'Updated the Duration of the ticket: {ticket_id}')
            tickets_found = True
        else:
            logger.info(f'No extended tickets for the TicketId: {ticket_id}')
        return tickets_found

    @typeguard.typechecked
    @logger_time_stamp
    def __close_and_update_ticket_data_in_es(self, ticket_id: str):
        """
        This method close the ticket and update in ElasticSearch
        :return:
        """
        data = {'timestamp': datetime.utcnow(), 'ticket_id_state': 'closed'}
        if self.__es_operations.check_elastic_search_connection():
            self.__es_operations.update_elasticsearch_index(index=self.__es_index_cro, id=ticket_id, metadata=data)
            self.__jira_operations.move_issue_state(ticket_id, state='CLOSED')

    @typeguard.typechecked
    @logger_time_stamp
    def _monitor_ticket_duration(self, ticket_id: str, region_name: str, duration: int, completed_duration: int, **kwargs):
        """
        This method monitors the ticket duration
        :param ticket_id:
        :param region_name:
        :param duration:
        :return:
        """
        user, cc = kwargs.get('user_cro'), self.__default_admins
        cc.append(kwargs.get('approved_manager'))
        remaining_duration = duration - completed_duration
        subject = body = None
        if remaining_duration <= FIRST_CRO_ALERT:
            ticket_extended = self.extend_ticket_duration(ticket_id=ticket_id, region_name=region_name,
                                                          current_duration=duration)
            if not ticket_extended:
                if remaining_duration == FIRST_CRO_ALERT:
                    subject, body = self.__mail_message.cro_monitor_alert_message(user=user, days=FIRST_CRO_ALERT, ticket_id=ticket_id)
                    message_type = 'first_duration_alert'
                elif remaining_duration == SECOND_CRO_ALERT:
                    subject, body = self.__mail_message.cro_monitor_alert_message(user=user, days=SECOND_CRO_ALERT, ticket_id=ticket_id)
                    message_type = 'second_duration_alert'
                else:
                    if remaining_duration <= CLOSE_JIRA_TICKET:
                        self.__close_and_update_ticket_data_in_es(ticket_id=ticket_id)
                        subject, body = self.__mail_message.cro_send_closed_alert(user, ticket_id)
                        message_type = 'ticket_closed_alert'
        if subject and body:
            self.__postfix.send_email_postfix(to=user, cc=cc, subject=subject, content=body, mime_type='html',
                                              message_type=message_type)

    @typeguard.typechecked
    @logger_time_stamp
    def _monitor_ticket_budget(self, ticket_id: str, region_name: str, budget: int, used_budget: int, **kwargs):
        """
        This method monitors the ticket budget
        :param ticket_id:
        :param region_name:
        :param budget:
        :param used_budget
        :return:
        """
        user, cc = kwargs.get('user_cro'), self.__default_admins
        remaining_budget = budget - used_budget
        threshold_budget = budget - (budget * (self.__ticket_over_usage_limit / 100))
        subject = body = None
        if threshold_budget >= remaining_budget > 0:
            ticket_extended = self.extend_tickets_budget(ticket_id=ticket_id, region_name=region_name,
                                                         current_budget=budget)
            if not ticket_extended:
                subject, body = self.__mail_message.cro_monitor_budget_remain_alert(user=user, budget=budget,
                                                                                    ticket_id=ticket_id,
                                                                                    used_budget=used_budget,
                                                                                    remain_budget=remaining_budget)
        elif remaining_budget <= 0:
            ticket_extended = self.extend_tickets_budget(ticket_id=ticket_id, region_name=region_name,
                                                         current_budget=budget)
            if not ticket_extended:
                subject, body = self.__mail_message.cro_monitor_budget_remain_high_alert(user=user, budget=budget,
                                                                                     ticket_id=ticket_id,
                                                                                     used_budget=used_budget,
                                                                                     remain_budget=remaining_budget)
        if subject and body:
            self.__postfix.send_email_postfix(to=user, cc=cc, subject=subject, content=body, mime_type='html',
                                              message_type='budget_exceed_alert')

    @logger_time_stamp
    def _monitor_in_progress_tickets(self):
        """
        This method monitors in-progress tickets
        :return:
        """
        in_progress_tickets_list = self._get_all_in_progress_tickets()
        for ticket_data in in_progress_tickets_list:
            source_data = ticket_data.get('_source')
            if source_data:
                ticket_id = source_data.get('ticket_id')
                region_name = source_data.get('region_name', '')
                if type(region_name) is list:
                    region_name = list(set(region_name))[0]
                budget = int(source_data.get('estimated_cost', 0))
                duration = int(source_data.get('duration', 0))
                used_budget = int(source_data.get('actual_cost', 0))
                ticket_start_date = datetime.strptime(source_data.get('ticket_opened_date'), DATE_FORMAT).date()
                completed_duration = (datetime.utcnow().date() - ticket_start_date).days
                self._monitor_ticket_budget(ticket_id=ticket_id, region_name=region_name, budget=budget,
                                            used_budget=used_budget,
                                            user_cro=source_data.get('user_cro'),
                                            approved_manager=source_data.get('approved_manager'))
                self._monitor_ticket_duration(ticket_id=ticket_id, region_name=region_name, duration=duration,
                                              completed_duration=completed_duration,
                                              user_cro=source_data.get('user_cro'),
                                              approved_manager=source_data.get('approved_manager')
                                              )

    def monitor_tickets(self):
        """
        This method monitor all tickets by status
        :return:
        """
        self._monitor_in_progress_tickets()
        self.update_cluster_cost()
