from abc import ABC
from datetime import datetime
from typing import Union


from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_runners.common.abstract_upload import AbstractUpload


class UploadElasticSearch(AbstractUpload, ABC):

    DEFAULT_UPLOAD_LIMIT = 500

    def __init__(self):
        super().__init__()
        self._es_operations = ElasticSearchOperations()
        self.__es_host = self._environment_variables_dict.get('es_host', '')

    def upload(self, data: Union[list, dict]):
        """
        This method upload data to ElasticSearch
        :return:
        :rtype:
        """
        if self.__es_host:
            if self._es_operations.check_elastic_search_connection():
                if data:
                    if len(data) > self.DEFAULT_UPLOAD_LIMIT:
                        self._es_operations.upload_data_in_bulk(data_items=data.copy(), index=self._es_index)
                    else:
                        for policy_dict in data:
                            if 'RegionName' not in policy_dict:
                                policy_dict['RegionName'] = self._region
                            if 'account' not in policy_dict:
                                policy_dict['account'] = self._account
                            self._es_operations.upload_to_elasticsearch(data=policy_dict.copy(), index=self._es_index)
                    logger.info(f'Uploaded the policy results to elasticsearch index: {self._es_index}')
                else:
                    logger.error(f'No data to upload on @{self._account}  at {datetime.utcnow()}')
            else:
                logger.error('ElasticSearch host is not pingable, Please check your connection')
