import uuid
from functools import wraps
from unittest.mock import patch, Mock

from azure.mgmt.subscription import SubscriptionClient


def mock_init(*args, **kwargs):
    """
    This method returns the mock call
    :return:
    :rtype:
    """
    pass


def mock_get_token(*args, **kwargs):
    """
    This method returns the mock token
    :param args:
    :type args:
    :param kwargs:
    :type kwargs:
    :return:
    :rtype:
    """
    return str(uuid.uuid1())


def mock_subscription(method):
    """
    This method is mock the azure compute operations
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
        with patch.object(SubscriptionClient, '__init__', mock_init):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
