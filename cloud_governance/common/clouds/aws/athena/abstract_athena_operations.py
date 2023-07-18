from abc import ABC, abstractmethod
from datetime import datetime

from cloud_governance.main.environment_variables import environment_variables


class AbstractAthenaOperations(ABC):

    CURRENT_DATE = str(datetime.utcnow().date()).replace("-", "")

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__s3_results_path = self.__environment_variables_dict.get('S3_RESULTS_PATH')
        super().__init__()

    def _get_s3_path(self):
        """
        This method returns the s3 path to dump athena results
        :return:
        """
        s3_path = f"{self.__s3_results_path}/{self.CURRENT_DATE}"
        return s3_path

    @abstractmethod
    def execute_query(self, query_string: str):
        """
        This method executes the query in aws athena
        :param query_string:
        :return:
        """
        raise NotImplemented()

