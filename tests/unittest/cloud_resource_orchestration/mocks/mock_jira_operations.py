
from functools import wraps
from unittest.mock import patch


from cloud_governance.common.jira.jira_operations import JiraOperations


def mock_get_issue(*args, **kwargs):
    """This method mock the get_issue from the jira"""
    if kwargs.get('jira_id'):
        return {'fields': {
            'status': {'name': 'Refinement'},
            'description': "First Name: Test\n"
                           "Last Name: Mock\nEmail Address: mock@gmail.com\n"
                           "Manager Approval Address: manager@gmail.com\nCC-Users: \nDays: 5\n"
                           "Project: mock-test\nRegion: ap-south-1\nFull Summary: This is the test mock test\n"
                           "Cloud Name: mock\nAccount Name: mock-account\nInstance Types: t2.micro: 5\n"
                           "Cost Estimation:12.0\nDetails: This is the test machine \n"
                           "ApprovedManager: mockapproval@gmail.com \n"
        }}


def mock_get_jira_id_sub_tasks(*args, **kwargs):
    """This method mock get_jira_id_sub_tasks"""
    if kwargs.get('jira_id'):
        return ['subtask-1']
    return {}


def mock_move_issue_state(*args, **kwargs):
    """this method mock mock_move_issue_state"""
    if kwargs.get('jira_id') and kwargs.get('state'):
        return True
    return False


def jira_mock(method):
    """
    Mocking the ibm SoftLayer client methods
    @param method:
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
        result = ''
        try:
            with patch.object(JiraOperations, 'get_issue', mock_get_issue), \
                    patch.object(JiraOperations, 'get_jira_id_sub_tasks', mock_get_jira_id_sub_tasks),\
                    patch.object(JiraOperations, 'move_issue_state', mock_move_issue_state):
                result = method(*args, **kwargs)
        except Exception as err:
            pass
        return result
    return method_wrapper
