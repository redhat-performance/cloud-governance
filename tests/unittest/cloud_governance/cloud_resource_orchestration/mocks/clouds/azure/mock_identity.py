import uuid
from functools import wraps
from unittest.mock import patch, Mock

from azure.identity import DefaultAzureCredential


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


def mock_identity(method):
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
        with patch.object(DefaultAzureCredential, '__init__', mock_init),\
             patch.object(DefaultAzureCredential, 'get_token', mock_get_token):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
