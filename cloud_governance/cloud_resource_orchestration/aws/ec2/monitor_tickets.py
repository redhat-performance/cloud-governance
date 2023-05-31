import logging
from datetime import datetime

import boto3
import typeguard

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.logger.init_logger import handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class MonitorTickets:
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
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__cro_resource_tag_name = self.__environment_variables_dict.get('CRO_RESOURCE_TAG_NAME')
        self.__jira_operations = JiraOperations()
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.es_cro_index = self.__environment_variables_dict.get('CRO_ES_INDEX', '')
        self.__default_admins = self.__environment_variables_dict.get('CRO_DEFAULT_ADMINS', [])
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME', '')
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()

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
            for ticket_id, description in tickets.items():
                if description.get('TicketOpenedDate').date() != datetime.now().date():
                    user = description.get('EmailAddress').split('@')[0]
                    manager = description.get('ManagerApprovalAddress').split('@')[0]
                    cc = self.__default_admins
                    if ticket_status == self.NEW:  # alert manager if didn't take any action
                        to = manager
                        subject, body = self.__mail_message.cro_request_for_manager_approval(manager=to, request_user=user, cloud_name=self.__cloud_name, ticket_id=ticket_id, description=description)
                        cc.append(description.get('EmailAddress'))
                    else:  # alert user if doesn't add tag name
                        to = user
                        cc.append(description.get('ManagerApprovalAddress'))
                        subject, body = self.__mail_message.cro_send_user_alert_to_add_tags(user=user, ticket_id=ticket_id)
                    if ticket_status in (self.NEW, self.REFINEMENT):
                        self.__postfix.send_email_postfix(to=to, cc=cc, subject=subject, content=body, mime_type='html')

    @typeguard.typechecked
    @logger_time_stamp
    def __track_in_progress_tickets(self, tickets: dict):
        """
        This method track the in-progress tickets
        :param tickets:
        :return:
        """
        current_date = datetime.now().date()
        for ticket_id, description in tickets.items():
            ticket_id = ticket_id.split('-')[-1]
            es_id_data = self.__es_operations.get_es_data_by_id(id=ticket_id, index=self.es_cro_index).get('_source')
            if es_id_data:
                ticket_opened_date = description.get('TicketOpenedDate').date()
                self.__region_name = description.get('Region')
                ticket_monitoring_days = (current_date - ticket_opened_date).days
                duration = int(es_id_data.get('duration'))
                remaining_duration = duration - ticket_monitoring_days
                handler.setLevel(logging.WARN)
                es_data_change = self.verify_es_instances_state(es_data=es_id_data)
                if es_data_change:
                    self.__es_operations.update_elasticsearch_index(index=self.es_cro_index, id=ticket_id, metadata=es_id_data)
                self.__alert_in_progress_ticket_users(ticket_id=ticket_id, es_id_data=es_id_data, remaining_duration=remaining_duration)
                handler.setLevel(logging.INFO)

    @typeguard.typechecked
    @logger_time_stamp
    def __tag_extend_instances(self, sub_tasks: list, ticket_id: str, duration: int, sub_task_count: int, estimated_cost: float):
        """
        This method extend the duration if the user opened expand ticket
        :param sub_tasks:
        :param ticket_id:
        :param duration:
        :param sub_task_count:
        :param estimated_cost:
        :return:
        """
        ticket_id = ticket_id.split('-')[-1]
        local_ec2_operations = EC2Operations(region=self.__region_name)
        local_ec2_client = boto3.client('ec2', region_name=self.__region_name)
        filters = {'Filters': [{'Name': f'tag:{self.__cro_resource_tag_name}', 'Values': [ticket_id]}]}
        extend_duration = 0
        for task_id in sub_tasks:
            description = self.__jira_operations.get_issue_description(ticket_id=task_id, sub_task=True)
            extend_duration += int(description.get('Days'))
        instance_ids = local_ec2_operations.get_ec2_instance_ids(**filters)
        if duration > 0:
            duration += extend_duration
            tags = [{'Key': 'Duration', 'Value': str(duration)}]
            local_ec2_operations.tag_ec2_resources(client_method=local_ec2_client.create_tags, resource_ids=instance_ids, tags=tags)
            data = {'duration': duration, 'timestamp': datetime.utcnow(), 'sub_tasks': len(sub_tasks) + sub_task_count, 'estimated_cost': round(estimated_cost, self.DEFAULT_ROUND_DIGITS)}
            if self.__es_operations:
                self.__es_operations.update_elasticsearch_index(metadata=data, id=ticket_id, index=self.es_cro_index)
            for task_id in sub_tasks:
                self.__jira_operations.move_issue_state(ticket_id=task_id, state='closed')

    @typeguard.typechecked
    @logger_time_stamp
    def __alert_in_progress_ticket_users(self, ticket_id: str, es_id_data: dict, remaining_duration: int):
        """
        This method alert the in-progress alert users
        :param ticket_id:
        :param es_id_data:
        :param remaining_duration:
        :return:
        """
        subject = body = None
        user, cc = es_id_data.get('user_cro'), self.__default_admins
        cc.append(es_id_data.get('approved_manager'))
        if remaining_duration <= self.FIRST_CRO_ALERT:
            sub_tasks = self.__jira_operations.get_ticket_id_sub_tasks(ticket_id=ticket_id)
            if sub_tasks:
                duration = es_id_data.get('duration')
                estimated_cost = float(es_id_data.get('estimated_cost'))
                sub_task_count = es_id_data.get('sub_tasks', 0)
                self.__tag_extend_instances(sub_tasks=sub_tasks, ticket_id=ticket_id, duration=duration, sub_task_count=sub_task_count, estimated_cost=estimated_cost)
        if remaining_duration == self.FIRST_CRO_ALERT:
            subject, body = self.__mail_message.cro_monitor_alert_message(user=user, days=self.FIRST_CRO_ALERT, ticket_id=ticket_id)
        elif remaining_duration == self.SECOND_CRO_ALERT:
            subject, body = self.__mail_message.cro_monitor_alert_message(user=user, days=self.SECOND_CRO_ALERT, ticket_id=ticket_id)
        else:
            if remaining_duration <= self.CLOSE_JIRA_TICKET:
                self.__update_ticket_elastic_data(ticket_id=ticket_id, es_id_data=es_id_data)
                subject, body = self.__mail_message.cro_send_closed_alert(user, es_id_data, ticket_id)
        if subject and body:
            self.__postfix.send_email_postfix(to=user, cc=cc, subject=subject, content=body, mime_type='html')

    @typeguard.typechecked
    @logger_time_stamp
    def __update_ticket_elastic_data(self, ticket_id: str, es_id_data: dict):
        """
        This method update the ticket data in elastic_search
        :param ticket_id:
        :param es_id_data:
        :return:
        """
        self.__jira_operations.move_issue_state(ticket_id, state='CLOSED')
        data = {'timestamp': datetime.utcnow(), 'ticket_id_state': 'closed'}
        es_id_data.update(data)
        self.__es_operations.update_elasticsearch_index(index=self.es_cro_index, id=ticket_id, metadata=es_id_data)

    @typeguard.typechecked
    @logger_time_stamp
    def verify_es_instances_state(self, es_data: dict):
        """
        This method verify the state of the es_instances
        :param es_data:
        :return:
        """
        instance_ids = [resource.split(',')[1].strip() for resource in es_data.get('instances') if 'terminated' not in resource]
        es_data_change = False
        if instance_ids:
            local_ec2_operations = EC2Operations(region=self.__region_name)
            instances = local_ec2_operations.get_ec2_instance_ids(Filters=[{'Name': 'instance-id', 'Values': instance_ids}])
            instance_ids = list(set(instance_ids) - set(instances))
            for idx, resource in enumerate(es_data.get('instances')):
                resource_data = resource.split(',')
                instance_id = resource_data[1].strip()
                if instance_id in instance_ids:
                    es_data_change = True
                    resource_data[4] = 'terminated'
                    es_data['instances'][idx] = ', '.join(resource_data)
        return es_data_change

    @logger_time_stamp
    def __track_tickets(self):
        """
        This method trak the user tickets
        :return:
        """
        for ticket_status in [self.NEW, self.REFINEMENT]:
            self.__send_ticket_status_alerts(ticket_status=ticket_status, tickets=self.get_tickets(ticket_status=ticket_status))
        self.__track_in_progress_tickets(self.get_tickets(ticket_status=self.IN_PROGRESS))

    @logger_time_stamp
    def run(self):
        """
        This method run all methods of jira tickets monitoring
        :return:
        """
        self.__track_tickets()
