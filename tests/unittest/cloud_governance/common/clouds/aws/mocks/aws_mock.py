from functools import wraps
from unittest.mock import patch

import pandas

from cloud_governance.common.clouds.aws.athena.abstract_athena_operations import AbstractAthenaOperations
from cloud_governance.common.clouds.aws.athena.boto3_client_athena_operations import BotoClientAthenaOperations
from cloud_governance.common.clouds.aws.athena.pyathena_operations import PyAthenaOperations


class ParameterNotFoundException(Exception):
    def __init__(self, parameter_name):
        self.parameter_name = parameter_name
        super().__init__(f"Parameter '{parameter_name}' not found.")

    def __str__(self):
        return f"ParameterNotFoundException: Parameter '{self.parameter_name}' not found."


def mock_execute_query(cls, *args, **kwargs):
    """
    This method mocks
    :param cls:
    :param args:
    :param kwargs:
    :return:
    """
    if kwargs.get('query_string'):
        data = {
            "A": [1, 2, 3],
            "B": [0, 1, 2]
        }
        df1 = pandas.DataFrame(data)
        return df1.to_dict(orient='records')
    else:
        raise ParameterNotFoundException('query_string')


def mock_athena(method):
    """
    Mocking aws athena
    :param method:
    :return:
    """
    @wraps(method)
    def method_wrapper(*args, **kwargs):
        """
        This is wrapper method to wrap the athena
        :param args:
        :param kwargs:
        :return:
        """
        try:
            with patch.object(PyAthenaOperations, 'execute_query', mock_execute_query), \
                 patch.object(BotoClientAthenaOperations, 'execute_query', mock_execute_query):
                result = method(*args, **kwargs)
        except Exception as err:
            raise err
        return result
    return method_wrapper
