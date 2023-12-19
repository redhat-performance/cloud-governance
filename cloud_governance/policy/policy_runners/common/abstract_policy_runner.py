import os.path
from abc import abstractmethod, ABC
from typing import Union

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.elasticsearch.upload_elastic_search import UploadElasticSearch


class AbstractPolicyRunner(ABC):

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._policy = self._environment_variables_dict.get('policy', '')
        self._account = self._environment_variables_dict.get('account', '')
        self._dry_run = self._environment_variables_dict.get('dry_run', 'yes')
        self._region = self._environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._run_active_regions = self._environment_variables_dict.get('RUN_ACTIVE_REGIONS')
        self._upload_elastic_search = UploadElasticSearch()
        self._save_to_file_path = self._environment_variables_dict.get('SAVE_TO_FILE_PATH')

    @abstractmethod
    def run(self):
        raise NotImplementedError("This method is not yet implemented")

    def write_to_file(self, data: Union[list, dict]):
        """
        This method writes the data to file_path passed by the env SAVE_TO_FILE_PATH
        :param data:
        :type data:
        :return:
        :rtype:
        """
        if self._save_to_file_path:
            if os.path.exists(self._save_to_file_path):
                if data:
                    header_added = False
                    file_name = f'{self._save_to_file_path}/{self._policy}.csv'
                    with open(file_name, 'w') as file:
                        if isinstance(data, list):
                            for item in data:
                                if not header_added:
                                    keys = [str(val) for val in list(item.keys())] + ["\n"]
                                    file.write(', '.join(keys))
                                    header_added = True
                                values = [str(val) for val in list(item.values())] + ["\n"]
                                file.write(', '.join(values))
                        else:
                            if isinstance(data, dict):
                                if not header_added:
                                    keys = [str(val) for val in list(data.keys())] + ["\n"]
                                    file.write(', '.join(keys))
                                    header_added = True
                                values = [str(val) for val in list(data.values())] + ["\n"]
                                file.write(', '.join(values))
                    logger.info(f"Written the data into the file_name: {file_name}")
            else:
                raise FileExistsError(f"FilePath not exists {self._save_to_file_path}")
