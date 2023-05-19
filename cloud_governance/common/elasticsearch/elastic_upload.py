from ast import literal_eval

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class ElasticUpload:

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.es_index = self.__environment_variables_dict.get('es_index', '')
        self.account = self.__environment_variables_dict.get('account', '').upper().replace('OPENSHIFT-', '').strip()
        self.special_user_mails = self.__environment_variables_dict.get('special_user_mails', '{}')
        self.postfix_mail = Postfix()
        self.mail_message = MailMessage()
        self.elastic_search_operations = ElasticSearchOperations(es_host=self.es_host, es_port=self.__es_port) if self.es_host else None

    def es_upload_data(self, items: list, es_index: str = '', **kwargs):
        """
        This method upload data to elastic search
        @param items:
        @param es_index:
        @return:
        """
        try:
            if not es_index:
                es_index = self.es_index
            count = 0
            for item in items:
                if not item.get('Account'):
                    item['Account'] = kwargs.get('Account') if kwargs.get('Account') else self.account
                if kwargs.get('set_index'):
                    self.elastic_search_operations.upload_to_elasticsearch(index=es_index, data=item, id=item[kwargs.get('set_index')])
                else:
                    self.elastic_search_operations.upload_to_elasticsearch(index=es_index, data=item)
                count += 1
            if count > 0 and len(items) > 0:
                logger.warn(f'Data Uploaded to {es_index} successfully, Total data: {count}')
        except Exception as err:
            logger.error(f'Error raised {err}')

    def literal_eval(self, data: any):
        """
        This method convert string object into its original datatype
        ex: "{'Project': 'Cloud-Governance'}" --> {'Project': 'Cloud-Governance'}
        @param data:
        @return:
        """
        if data:
            return literal_eval(data)
        return data
