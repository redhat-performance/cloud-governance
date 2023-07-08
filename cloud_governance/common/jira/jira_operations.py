import asyncio
import json
import os.path
from datetime import datetime

import typeguard

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.jira.jira import Jira
from cloud_governance.main.environment_variables import environment_variables


class JiraOperations:
    """
    This Class is used for jira operations for cloud-governance
    """

    REFINEMENT = 'Refinement'
    IN_PROGRESS = 'In Progress'
    JIRA_TRANSITION_IDS = {
        'NEW': 51, 'REFINEMENT': 61, 'INPROGRESS': 31, 'CLOSED': 41, 'ANY': 0
    }
    FILE_EXTENSION = '.json'

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__jira_url = self.__environment_variables_dict.get('JIRA_URL').strip()
        self.__jira_username = self.__environment_variables_dict.get('JIRA_USERNAME').strip()
        self.__jira_token = self.__environment_variables_dict.get('JIRA_TOKEN').strip()
        self.__jira_queue = self.__environment_variables_dict.get('JIRA_QUEUE').strip()
        self.__cache_temp_dir = self.__environment_variables_dict.get('TEMPORARY_DIRECTORY', '').strip()
        self.__loop = asyncio.new_event_loop()
        self.__jira_object = Jira(url=self.__jira_url, username=self.__jira_username, token=self.__jira_token, ticket_queue=self.__jira_queue, loop=self.__loop)

    @typeguard.typechecked
    @logger_time_stamp
    def move_issue_state(self, ticket_id: str, state: str):
        """
        This method move the issue state
        :param ticket_id:
        :param state:
        :return:
        """
        if '-' in ticket_id:
            ticket_id = ticket_id.split('-')[-1]
        state_id = self.JIRA_TRANSITION_IDS.get(state.upper())
        return self.__loop.run_until_complete(self.__jira_object.post_transition(ticket=ticket_id, transition=state_id))

    @typeguard.typechecked
    @logger_time_stamp
    def get_issue(self, ticket_id: str):
        """
        This method returns the issue data
        :param ticket_id:
        :return:
        """
        return self.__loop.run_until_complete(self.__jira_object.get_ticket(ticket=ticket_id))

    @typeguard.typechecked
    @logger_time_stamp
    def return_cache_ticket_description(self, ticket_id: str):
        """
        This method checks ticket id is already fetched from jira api
        :param ticket_id:
        :return:
        """
        with open(f'{self.__cache_temp_dir}/{ticket_id}{self.FILE_EXTENSION}') as cache_ticket_description:
            result_data = json.load(cache_ticket_description)
            result_data['TicketOpenedDate'] = datetime.strptime(result_data.get('TicketOpenedDate'), "%Y-%m-%d %H:%M:%S")
            return result_data

    @typeguard.typechecked
    @logger_time_stamp
    def cache_ticket_description(self, ticket_id: str, ticket_description: dict):
        """
        This method saves the ticket_id description
        :param ticket_description:
        :param ticket_id:
        :return:
        """
        if self.__cache_temp_dir:
            with open(f'{self.__cache_temp_dir}/{ticket_id}{self.FILE_EXTENSION}', 'w') as cache_ticket_description:
                json.dump(ticket_description, cache_ticket_description, default=str)

    @typeguard.typechecked
    @logger_time_stamp
    def get_issue_description(self, ticket_id: str, state: str = '', sub_task: bool = False):
        """
        This method return the ticket data description
        :param ticket_id:
        :param state:
        :param sub_task:
        :return:
        """
        if '-' in ticket_id:
            ticket_id = ticket_id.split('-')[-1]
        if os.path.exists(f'{self.__cache_temp_dir}/{ticket_id}{self.FILE_EXTENSION}'):
            return self.return_cache_ticket_description(ticket_id=ticket_id)
        else:
            issue_data = self.get_issue(ticket_id=ticket_id)
            if issue_data:
                if issue_data['fields']['status']['name'] == self.REFINEMENT or self.JIRA_TRANSITION_IDS.get(state, -1) == 0 or (state == 'INPROGRESS' and issue_data['fields']['status']['name'] == self.IN_PROGRESS) or sub_task:
                    description_list = issue_data['fields']['description'].split('\n')
                    description_dict = {}
                    for description in description_list:
                        if description:
                            values = description.strip().split(':', 1)
                            if len(values) == 2:
                                key, value = values
                                description_dict[key.strip().replace(' ', '')] = value.strip()
                    if 'Project' in description_dict:
                        if description_dict['Project'] == "Other":
                            description_dict['Project'] = description_dict.get('Explanationof"Other"primaryproduct')
                            if not description_dict['Project']:
                                description_dict['Project'] = description_dict.get('Otherproductsbeingtested')
                            if not description_dict['Project']:
                                description_dict['Project'] = description_dict.get('Explanationof"Other"secondaryproduct')
                    description_dict['TicketOpenedDate'] = datetime.strptime(issue_data.get('fields').get('created').split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    description_dict['JiraStatus'] = issue_data['fields']['status']['name']
                    self.cache_ticket_description(ticket_id=ticket_id, ticket_description=description_dict)
                    return description_dict
        return {}

    @logger_time_stamp
    def get_all_issues_in_progress(self):
        """
        This method get all issues which are in progress
        :return:
        """
        issues = self.__loop.run_until_complete(self.__jira_object.search_tickets(query={'Status': "'IN PROGRESS'"})).get('issues')
        ticket_ids = {}
        for issue in issues:
            if '[Clouds]' in issue['fields']['summary']:
                ticket_id = issue.get('key')
                description = self.beautify_issue_description(issue['fields']['description'])
                description['TicketOpenedDate'] = datetime.strptime(issue.get('fields').get('created').split('.')[0], "%Y-%m-%dT%H:%M:%S")
                ticket_ids[ticket_id] = description.get('Region')
        return ticket_ids

    @logger_time_stamp
    def beautify_issue_description(self, description):
        """
        This method beautify the issue description
        """
        description = description.split("\n")
        description_data = {}
        for index, line in enumerate(description):
            if line:
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    description_data[key.strip().replace(' ', '')] = value.strip()
                else:
                    description_data[index] = line.strip()
        return description_data

    @typeguard.typechecked
    @logger_time_stamp
    def get_ticket_id_sub_tasks(self, ticket_id: str, closed: bool = False):
        """
        This method returns th list of subtasks
        :param ticket_id:
        :param closed:
        :return:
        """
        ticket_id = ticket_id.split("-")[-1]
        jira_data = self.get_issue(ticket_id=ticket_id)
        if jira_data:
            sub_tasks_ids = []
            sub_tasks = jira_data.get('fields', {}).get('subtasks', {})
            if sub_tasks:
                for sub_task in sub_tasks:
                    fields = sub_task.get('fields')
                    if fields.get('status').get('name') != 'Closed' or closed:
                        sub_tasks_ids.append(sub_task.get('key'))
            return sub_tasks_ids
        return []

    @typeguard.typechecked
    @logger_time_stamp
    def get_issue_sub_tasks_cost_estimation(self, ticket_id: str):
        """
        This method get issue cost estimation
        :param ticket_id:
        :return:
        """
        sub_tasks = self.get_ticket_id_sub_tasks(ticket_id=ticket_id, closed=True)
        cost_estimation = 0
        for sub_task in sub_tasks:
            description = self.get_issue_description(ticket_id=sub_task, sub_task=True)
            cost_estimation += float(description.get('CostEstimation', 0))
        return cost_estimation

    @typeguard.typechecked
    def get_issue_sub_tasks_duration(self, ticket_id: str):
        """
        This method return the issue sub-tasks total duration
        :param ticket_id:
        :return:
        """
        sub_tasks = self.get_ticket_id_sub_tasks(ticket_id=ticket_id, closed=True)
        total_duration = 0
        for sub_task in sub_tasks:
            description = self.get_issue_description(ticket_id=sub_task, sub_task=True)
            total_duration += int(description.get('Days', 0))
        return total_duration

    @typeguard.typechecked
    @logger_time_stamp
    def get_all_issues(self, ticket_status: str):
        """
        This method get all issues which are in progress
        :param ticket_status:
        :return:
        """
        issues = self.__loop.run_until_complete(
            self.__jira_object.search_tickets(query={'Status': f"'{ticket_status}'"})).get('issues')
        ticket_ids = {}
        for issue in issues:
            if '[Clouds]' in issue['fields']['summary']:
                ticket_id = issue.get('key')
                description = self.beautify_issue_description(issue['fields']['description'])
                description['TicketOpenedDate'] = datetime.strptime(issue.get('fields').get('created').split('.')[0], "%Y-%m-%dT%H:%M:%S")
                ticket_ids[ticket_id] = description
        return ticket_ids
