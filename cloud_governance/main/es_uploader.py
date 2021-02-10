
from cloud_governance.common.es.es_operations import ESOperations


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
        self.__regions_name = kwargs.get('regions')
        self.__policies_name = kwargs.get('policies')

    def upload_to_es(self):
        """
        This method upload data to input ELK
        """
        for region in self.__regions_name:
            for policy in self.__policies_name:
                elk_operations = ESOperations(es_host=self.__es_host, es_port=self.__es_port, region=region, bucket=self.__bucket_name, logs_bucket_key=self.__logs_bucket_key)
                self.__es_add_items.update({'policy': policy, 'region': region})
                elk_operations.upload_last_policy_to_es(policy=policy, index=self.__es_index, doc_type=self.__es_doc_type, s3_json_file=self.__s3_file_name,
                                                               es_add_items=self.__es_add_items)


