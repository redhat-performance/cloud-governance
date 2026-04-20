from datetime import datetime, timedelta, timezone
from functools import wraps
from unittest.mock import patch

from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.main.environment_variables import environment_variables

# Jira() is still constructed with real credentials; CI often has no JIRA_* env vars.
_JIRA_STANDIN_KEYS = ('JIRA_USERNAME', 'JIRA_URL', 'JIRA_QUEUE')
_JIRA_STANDIN_DEFAULTS = {
    'JIRA_USERNAME': 'mock@example.com',
    'JIRA_URL': 'https://mock.atlassian.net',
    'JIRA_QUEUE': 'MOCK',
}


def get_ticket_response():
    """
    This method return the ticket data
    :return:
    """
    created = datetime.strftime(datetime.now(tz=timezone.utc) - timedelta(days=2), "%Y-%m-%dT%H:%M:%S")
    response = {
                'key': 'MOCK-1',
                'fields': {
                    'status': {'name': 'Refinement'},
                    'created': created,
                    'description': "First Name: Test\n"
                                   "Last Name: Mock\nEmail Address: mock@gmail.com\n"
                                   "Manager Approval Address: manager@gmail.com\nCC-Users: \nDays: 5\n"
                                   "Project: mock-test\nRegion: ap-south-1\nFull Summary: This is the test mock test\n"
                                   "Cloud Name: mock\nAccount Name: mock-account\nInstance Types: t2.micro: 5\n"
                                   "Cost Estimation:12.0\nDetails: This is the test machine \n"
                                   "ApprovedManager: mockapproval@gmail.com \n"
                                   "Region: ap-south-1 \n"
                }
            }

    return response


def mock_get_issue(*args, **kwargs):
    """
    This method is mock for the get ticket data
    :param kwargs:
    :return:
    """
    if kwargs.get('ticket_id'):
        return get_ticket_response()


def mock_move_issue_state(*args, **kwargs):
    """
    This method is mocking for moving Jira tickets
    :param kwargs:
    :return:
    """
    if kwargs.get('ticket_id') and kwargs.get('state'):
        return True
    return False


async def mock_get_all_issues(*args, **kwargs):
    """
    This method is mocking for search all tickets
    :param args:
    :param kwargs:
    :return:
    """
    if kwargs.get('query'):
        response = {
            'issues': {
                'key': 'MOCK-1',
                'fields': {
                    'status': {'name': 'Refinement'},
                    'created': datetime.now(tz=timezone.utc) - timedelta(days=2),
                    'description': "First Name: Test\n"
                                   "Last Name: Mock\nEmail Address: mock@gmail.com\n"
                                   "Manager Approval Address: manager@gmail.com\nCC-Users: \nDays: 5\n"
                                   "Project: mock-test\nRegion: ap-south-1\nFull Summary: This is the test mock test\n"
                                   "Cloud Name: mock\nAccount Name: mock-account\nInstance Types: t2.micro: 5\n"
                                   "Cost Estimation:12.0\nDetails: This is the test machine \n"
                                   "ApprovedManager: mockapproval@gmail.com \n"
                                   "Region: ap-south-1 \n"
                }
            }
        }
        return response


def mock_jira(method):
    """
    This method is mocking for Jira class methods which are used in Jira Operations    @param method:
    @return:
    """

    @wraps(method)
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        env = environment_variables.environment_variables_dict
        saved_jira = {k: env.get(k, '') for k in _JIRA_STANDIN_KEYS}
        try:
            for key, default in _JIRA_STANDIN_DEFAULTS.items():
                if not (env.get(key) or '').strip():
                    env[key] = default
            with patch.object(JiraOperations, 'get_issue', mock_get_issue),\
                    patch.object(JiraOperations, 'move_issue_state', mock_move_issue_state), \
                    patch.object(JiraOperations, 'get_all_issues', mock_get_all_issues):
                result = method(*args, **kwargs)
            return result
        finally:
            for key in _JIRA_STANDIN_KEYS:
                env[key] = saved_jira[key]

    return method_wrapper
