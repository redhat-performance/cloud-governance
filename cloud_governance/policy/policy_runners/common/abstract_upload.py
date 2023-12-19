from abc import ABC, abstractmethod
from typing import Union

from cloud_governance.main.environment_variables import environment_variables


class AbstractUpload(ABC):

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._account = self._environment_variables_dict.get('account', '')
        self._region = self._environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._es_index = self._environment_variables_dict.get('es_index')
        self._policy_output = self._environment_variables_dict.get('policy_output', '')
        self._policy = self._environment_variables_dict.get('policy', '')

    @abstractmethod
    def upload(self, data: Union[list, dict]):
        """
        This method upload data
        :return:
        :rtype:
        """
        raise NotImplemented("This is not yet implemented")
