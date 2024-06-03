import json
import tempfile
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


class AWSMonitorTickets(AbstractMonitorTickets):
    """This method monitor the Jira Tickets"""

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
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__cro_resource_tag_name = self.__environment_variables_dict.get('CRO_RESOURCE_TAG_NAME')
        self.__jira_operations = JiraOperations()
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.es_cro_index = self.__environment_variables_dict.get('CRO_ES_INDEX', '')
        self.__default_admins = self.__environment_variables_dict.get('CRO_DEFAULT_ADMINS', [])
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME', '')
        self.__account = self.__environment_variables_dict.get('account', '')
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self.__manager_escalation_days = self.__environment_variables_dict.get('MANAGER_ESCALATION_DAYS')
        self.__ldap_search = LdapSearch(self.__environment_variables_dict.get('LDAP_HOST_NAME'))
        self.__global_admin_name = self.__environment_variables_dict.get('GLOBAL_CLOUD_ADMIN')
        self.__database_name = self.__environment_variables_dict.get('ATHENA_DATABASE_NAME')
        self.__table_name = self.__environment_variables_dict.get('ATHENA_TABLE_NAME')
        self.__athena_account_access_key = self.__environment_variables_dict.get('ATHENA_ACCOUNT_ACCESS_KEY')
        self.__athena_account_secret_key = self.__environment_variables_dict.get('ATHENA_ACCOUNT_SECRET_KEY')
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()
        self.__ec2_operations = EC2Operations()

    @typeguard.typechecked
    @logger_time_stamp
    def get_tickets(self, ticket_status: str):
        """
        This method return the tickets based on status
        :param ticket_status:
        :return:
        """
        return self.__jira_operations.get_all_issues(ticket_status=ticket_status)

    @typeguard.typechecked
    @logger_time_stamp
    def __send_ticket_status_alerts(self, tickets: dict, ticket_status: str):
        """
        This method send alert to user Ticket status if it is on New, Refinement states
        Ticket States:
            New - Need approval
            Refinement - User didn't add the tag to the resources
        :param tickets:
        :param ticket_status:
        :return:
        """
        if ticket_status in (self.NEW, self.REFINEMENT):
            user_tickets = {}
            for ticket_id, description in tickets.items():
                ticket_id = ticket_id.split('-')[-1]
                if self.__account in description.get('AccountName'):
                    if not self.__es_operations.verify_elastic_index_doc_id(index=self.es_cro_index, doc_id=ticket_id):
                        if ticket_status == self.REFINEMENT:
                            ticket_status = 'manager-approved'
                        source = {'cloud_name': description.get('CloudName'), 'account_name': description.get('AccountName').replace('OPENSHIFT-', ''),
                                  'region_name': description.get('Region'), 'user': '',
                                  'user_cro': description.get('EmailAddress').split('@')[0], 'user_cost': 0, 'ticket_id': ticket_id, 'ticket_id_state': ticket_status.lower(),
                                  'estimated_cost': description.get('CostEstimation'), 'instances_count': 0, 'monitored_days': 0,
                                  'ticket_opened_date': description.get('TicketOpenedDate').date(), 'duration': description.get('Days'), 'approved_manager': '',
                                  'user_manager': '', 'project': description.get('Project'), 'owner': f'{description.get("FirstName")} {description.get("LastName")}'.upper(), 'total_spots': 0,
                                  'total_ondemand': 0, 'AllocatedBudget': [], 'instances_list': [], 'instance_types_list': []}
                        self.__es_operations.upload_to_elasticsearch(index=self.es_cro_index, data=source, id=ticket_id)
                    current_date = datetime.now().date()
                    ticket_opened_date = description.get('TicketOpenedDate').date()
                    if ticket_opened_date != current_date:
                        user = description.get('EmailAddress').split('@')[0]
                        manager = description.get('ManagerApprovalAddress').split('@')[0]
                        cc = self.__default_admins
                        subject = body = to = None
                        ticket_opened_days = (current_date - ticket_opened_date).days
                        if ticket_status == self.NEW:  # alert manager if didn't take any action
                            to = manager
                            extra_message = ''
                            if self.__manager_escalation_days <= ticket_opened_days <= self.__manager_escalation_days + 2:
                                manager_of_manager = self.__ldap_search.get_user_details(user_name=manager)
                                to = manager_of_manager.get('ManagerId', '')
                                extra_message = f"Your associate/Manager: [{manager}] doesn't approve this request.<br/>The user {user} is waiting for approval for last {ticket_opened_days} days.<br/>" \
                                                f"Please review the below details and approve/ reject"
                            elif ticket_opened_days >= self.__manager_escalation_days + 2:
                                to = self.__global_admin_name
                                extra_message = f"<b>Missing manager approval.<br />The user {user} is waiting for approval for last {ticket_opened_days} days.<br/>Please review the below details and approve/reject"
                            subject, body = self.__mail_message.cro_request_for_manager_approval(manager=to, request_user=user, cloud_name=self.__cloud_name, ticket_id=ticket_id, description=description, extra_message=extra_message)
                        else:  # alert user if doesn't add tag name
                            user_tickets.setdefault(user, []).append(f"{ticket_id} : {description.get('Project')}")
            if user_tickets:
                for user, ticket_ids in user_tickets.items():
                    active_instances = self.__ec2_operations.get_active_instances(ignore_tag='TicketId', tag_value=user, tag_name='User')
                    if active_instances:
                        for region, instances_list in active_instances.items():
                            active_instances_ids = {region: [instance.get('InstanceId') for instance in instances_list]}
                            to = user
                            cc = self.__default_admins
                            subject, body = self.__mail_message.cro_send_user_alert_to_add_tags(user=user, ticket_ids=ticket_ids)
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as filename:
                                filename.write(json.dumps(active_instances_ids))
                                filename.flush()
                                self.__postfix.send_email_postfix(to=to, cc=cc, subject=subject, content=body, mime_type='html', filename=filename.name)

    @logger_time_stamp
    def __track_tickets(self):
        """
        This method trak the user tickets
        :return:
        """
        self.__send_ticket_status_alerts(ticket_status=self.NEW, tickets=self.get_tickets(ticket_status=self.NEW))
        self.__send_ticket_status_alerts(ticket_status=self.REFINEMENT, tickets=self.get_tickets(ticket_status=self.REFINEMENT))

    def update_budget_tag_to_resources(self, region_name: str, ticket_id: str, updated_budget: int):
        """
        This method updates the budget to the aws resources which have the tag TicketId: #
        :param region_name:
        :param ticket_id:
        :param updated_budget:
        :return:
        """
        try:
            tag_to_be_updated = 'EstimatedCost'
            tagging_operations = AWSTaggingOperations(region_name=region_name)
            resources_list_to_update = tagging_operations.get_resources_list(tag_name='TicketId', tag_value=ticket_id)
            if resources_list_to_update:
                resource_arn_list = []
                previous_cost = 0
                for resource in resources_list_to_update:
                    resource_arn_list.append(resource.get('ResourceARN'))
                    if previous_cost == 0:
                        previous_cost = get_tag_value_by_name(tags=resource.get('Tags'), tag_name=tag_to_be_updated)
                updated_budget += int(float(previous_cost))
                update_tags_dict = {tag_to_be_updated: str(updated_budget)}
                tagging_operations.tag_resources_list(resources_list=resource_arn_list,
                                                      update_tags_dict=update_tags_dict)
            else:
                logger.info('No AWS resources to update the costs')
        except Exception as err:
            logger.error(err)

    def update_duration_tag_to_resources(self, region_name: str, ticket_id: str, updated_duration: int):
        """
        This method updates the budget to cloud resources
        :param region_name:
        :param ticket_id:
        :param updated_duration:
        :return:
        """
        try:
            tag_to_be_updated = 'Duration'
            tagging_operations = AWSTaggingOperations(region_name=region_name)
            resources_list_to_update = tagging_operations.get_resources_list(tag_name='TicketId', tag_value=ticket_id)
            if resources_list_to_update:
                resource_arn_list = []
                previous_duration = 0
                for resource in resources_list_to_update:
                    resource_arn_list.append(resource.get('ResourceARN'))
                    if previous_duration == 0:
                        previous_duration = get_tag_value_by_name(tags=resource.get('Tags'), tag_name=tag_to_be_updated)
                updated_duration += int(float(previous_duration))
                update_tags_dict = {tag_to_be_updated: str(updated_duration)}
                tagging_operations.tag_resources_list(resources_list=resource_arn_list, update_tags_dict=update_tags_dict)
            else:
                logger.info('No AWS resources to update the costs')
        except Exception as err:
            logger.error(err)

    def update_cluster_cost(self):
        """
        This method updates the cluster cost.
        :return:
        :rtype:
        """
        in_progress_tickets = self._get_all_in_progress_tickets()
        for ticket_data in in_progress_tickets:
            source_data = ticket_data.get('_source')
            if source_data:
                ticket_id = source_data.get('ticket_id')
                cluster_names = source_data.get('cluster_names', [])
                if cluster_names:
                    query = self.__prepare_athena_query_for_cluster_cost(names=cluster_names)
                    pyathena_operations = PyAthenaOperations(aws_access_key_id=self.__athena_account_access_key,
                                                             aws_secret_access_key=self.__athena_account_secret_key)
                    response = pyathena_operations.execute_query(query_string=query)
                    if response:
                        cluster_cost = {item.get('ClusterName'): item.get('UnblendedCost') for item in response}
                        self.__es_operations.update_elasticsearch_index(index=self.es_cro_index, id=ticket_id,
                                                                        metadata={
                                                                            'cluster_cost': cluster_cost,
                                                                            'timestamp': datetime.utcnow()
                                                                        })

    def __prepare_athena_query_for_cluster_cost(self, names: list):
        """
        This method returns the athena query to get results
        :param names:
        :type names:
        :return:
        :rtype:
        """
        query = ''
        if names:
            cluster_names = [f""" "resource_tags_user_name" LIKE '%{i}%' """ for i in names]
            case_statement = "CASE"
            for cluster_name in names:
                case_statement += f"""\nWHEN resource_tags_user_name like '%{cluster_name}%' THEN '{cluster_name}' """
            case_statement += "\nELSE resource_tags_user_name END as ClusterName"
            query = f"""
            SELECT
            line_item_usage_account_id as AccountId,
            {case_statement},
            ROUND(SUM(line_item_unblended_cost), 3) as UnblendedCost
            FROM "{self.__database_name}"."{self.__table_name}"
            where {"or ".join(cluster_names)}
            group by 1, 2
            """
        return query

    @logger_time_stamp
    def run(self):
        """
        This method run all methods of jira tickets monitoring
        :return:
        # """
        self.__track_tickets()
        self.monitor_tickets()
