import os
from ast import literal_eval

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix


class ElasticUpload:

    def __init__(self):
        self.__es_host = os.environ.get('es_host', '')
        self.__es_port = os.environ.get('es_port', '')
        self._es_index = os.environ.get('es_index', '')
        self.account = os.environ.get('account', '').upper()
        self._special_user_mails = os.environ.get('special_user_mails', '{}')
        self._postfix_mail = Postfix()
        self._mail_message = MailMessage()
        if self.__es_host:
            self._elastic_search_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)

    def es_upload_data(self, items: list, es_index: str):
        """
        This method upload data to elastic search
        @param items:
        @param es_index:
        @return:
        """
        count = 0
        for item in items:
            self._elastic_search_operations.upload_to_elasticsearch(index=es_index, data=item)
            count += 1
        if count > 0 and len(items) > 0:
            logger.info(f'Data Uploaded to {es_index} successfully')

    def _literal_eval(self, data: any):
        """
        This method convert string object into its original datatype
        ex: "{'Project': 'Cloud-Governance'}" --> {'Project': 'Cloud-Governance'}
        @param data:
        @return:
        """
        if data:
            return literal_eval(data)
        return data
