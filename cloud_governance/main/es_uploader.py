
from cloud_governance.common.es.es_operations import ESOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class ESUploader:
    """
    This class upload data to elastic search from s3 bucket
    """
    def __init__(self, **kwargs):
        self.__es_host = kwargs.get('es_host')
        self.__es_port = kwargs.get('es_port')
        self.__es_index = kwargs.get('es_index')
        self.__es_doc_type = kwargs.get('es_doc_type')
        self.__es_add_items = kwargs.get('es_add_items')
        self.__bucket_name = kwargs.get('bucket')
        self.__s3_file_name = kwargs.get('s3_file_name')
        self.__logs_bucket_key = kwargs.get('logs_bucket_key')
        self.__region_name = kwargs.get('region')
        self.__policy_name = kwargs.get('policy')

    @logger_time_stamp
    def upload_to_es(self, account):
        """
        This method upload data to input ELK
        """
        es_operations = ESOperations(es_host=self.__es_host, es_port=self.__es_port, region=self.__region_name, bucket=self.__bucket_name, logs_bucket_key=self.__logs_bucket_key)
        self.__es_add_items.update({'policy': self.__policy_name, 'region': self.__region_name})
        es_operations.upload_last_policy_to_es(policy=self.__policy_name, index=self.__es_index, doc_type=self.__es_doc_type, s3_json_file=self.__s3_file_name,
                                               es_add_items=self.__es_add_items)


