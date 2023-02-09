import asyncio

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.jira.jira import Jira
from cloud_governance.main.environment_variables import environment_variables


class JiraOperations:
    """
    This Class is used for jira operations for cloud-governance
    """

    REFINEMENT = 'Refinement'
    JIRA_TRANSITION_IDS = {
        'NEW': 51, 'REFINEMENT': 61, 'INPROGRESS': 31, 'CLOSED': 41
    }

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__jira_url = self.__environment_variables_dict.get('JIRA_URL').strip()
        self.__jira_username = self.__environment_variables_dict.get('JIRA_USERNAME').strip()
        self.__jira_token = self.__environment_variables_dict.get('JIRA_TOKEN').strip()
        self.__jira_queue = self.__environment_variables_dict.get('JIRA_QUEUE').strip()
        self.__loop = asyncio.new_event_loop()
        self.__jira_object = Jira(url=self.__jira_url, username=self.__jira_username, token=self.__jira_token, ticket_queue=self.__jira_queue, loop=self.__loop)

    @logger_time_stamp
    def move_issue_state(self, jira_id: str, state: str):
        """
        This method close the issue
        """
        if '-' in jira_id:
            jira_id = jira_id.split('-')[-1]
        state_id = self.JIRA_TRANSITION_IDS.get(state.upper())
        return self.__loop.run_until_complete(self.__jira_object.post_transition(ticket=jira_id, transition=state_id))

    @logger_time_stamp
    def get_issue(self, jira_id: str):
        """
        This method returns the issue data
        """
        return self.__loop.run_until_complete(self.__jira_object.get_ticket(ticket=jira_id))

    @logger_time_stamp
    def get_issue_description(self, jira_id: str, state: str = '', sub_task: bool = False):
        if '-' in jira_id:
            jira_id = jira_id.split('-')[-1]
        issue_data = self.get_issue(jira_id=jira_id)
        if issue_data:
            if issue_data['fields']['status']['name'] == self.REFINEMENT or state.upper() == 'ANY' or (state == self.JIRA_TRANSITION_IDS.get('INPROGRESS') and issue_data['fields']['status']['name'] == 'In Progress') or sub_task:
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
                return description_dict
        return {}

    @logger_time_stamp
    def get_all_issues_in_progress(self):
        """This method get all issues which are in progress"""
        issues = self.__loop.run_until_complete(self.__jira_object.search_tickets(query={'Status': "'IN PROGRESS'"})).get('issues')
        jira_ids = {}
        for issue in issues:
            if '[Clouds]' in issue['fields']['summary']:
                jira_id = issue.get('key')
                description = self.beautify_issue_description(issue['fields']['description'])
                jira_ids[jira_id] = description.get('Region')
        return jira_ids

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

    @logger_time_stamp
    def get_jira_id_sub_tasks(self, jira_id: str, closed: bool = False):
        """This method returns th list of subtasks"""
        jira_id = jira_id.split("-")[-1]
        jira_data = self.__loop.run_until_complete(self.__jira_object.get_ticket(ticket=jira_id))
        if jira_data:
            sub_tasks_ids = []
            sub_tasks = jira_data.get('fields').get('subtasks')
            for sub_task in sub_tasks:
                fields = sub_task.get('fields')
                if fields.get('status').get('name') != 'Closed' or closed:
                    sub_tasks_ids.append(sub_task.get('key'))
            return sub_tasks_ids
        return []

    def get_issue_sub_tasks_cost_estimation(self, jira_id: str):
        """This method get issue cost estimation"""
        sub_tasks = self.get_jira_id_sub_tasks(jira_id=jira_id, closed=True)
        cost_estimation = 0
        for sub_task in sub_tasks:
            description = self.get_issue_description(jira_id=sub_task, sub_task=True)
            cost_estimation += float(description.get('CostEstimation', 0))
        return cost_estimation


