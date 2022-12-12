
from cloud_governance.main.environment_variables import environment_variables


class IBMOperations:
    """
    This class contain the common parameters of ibm polices
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self._account = self.__environment_variables_dict.get('account', '')
        self._dry_run = self.__environment_variables_dict.get('dry_run', 'yes')
        self._policy = self.__environment_variables_dict.get('policy', '')
        self._tag_operation = self.__environment_variables_dict.get('tag_operation', 'read')




