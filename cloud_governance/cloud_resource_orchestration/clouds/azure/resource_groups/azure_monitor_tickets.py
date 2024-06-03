

import json
import tempfile
from abc import ABC
from datetime import datetime

import typeguard

from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.aws_tagging_operations import AWSTaggingOperations
from cloud_governance.cloud_resource_orchestration.common.abstract_monitor_tickets import AbstractMonitorTickets
from cloud_governance.cloud_resource_orchestration.utils.common_operations import get_tag_value_by_name
from cloud_governance.common.clouds.aws.athena.pyathena_operations import PyAthenaOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import handler, logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class AzureMonitorTickets(AbstractMonitorTickets):
    """This method monitors the Jira Tickets"""

    NEW = 'New'
    REFINEMENT = 'Refinement'
    CLOSED = 'Closed'
    IN_PROGRESS = 'In Progress'
    CLOSE_JIRA_TICKET = 0
    FIRST_CRO_ALERT: int = 5
    SECOND_CRO_ALERT: int = 3
    DEFAULT_ROUND_DIGITS: int = 3

    def __init__(self, region_name: str = ''):
        super().__init__()

    # Todo All the below methods implement in future releases
    def update_budget_tag_to_resources(self, region_name: str, ticket_id: str, updated_budget: int):
        pass

    def update_duration_tag_to_resources(self, region_name: str, ticket_id: str, updated_duration: int):
        pass

    def update_cluster_cost(self):
        pass

    def extend_tickets_budget(self, ticket_id: str, region_name: str, current_budget: int = 0):
        return super().extend_tickets_budget(ticket_id, region_name, current_budget)

    def extend_ticket_duration(self, ticket_id: str, region_name: str, current_duration: int = 0):
        return super().extend_ticket_duration(ticket_id, region_name, current_duration)

    @logger_time_stamp
    def run(self):
        """
        This method run all methods of jira tickets monitoring
        :return:
        # """
        self.monitor_tickets()
