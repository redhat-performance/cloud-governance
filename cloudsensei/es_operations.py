import logging
import os
from datetime import datetime

from elasticsearch import Elasticsearch


class ESOperations:
    """
    This class performs es operations
    """

    ES_INDEX = "cloudsensei"
    ES_DOC = '_doc'

    def __init__(self):
        self.__es_server = os.environ.get('ES_SERVER')
        self.__es = Elasticsearch(self.__es_server)

    def upload_to_es(self, data: dict, **kwargs):
        """
        This method uploads data to es
        :return:
        """
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()  # datetime.now()
        # Upload data to elastic search server
        try:
            self.__es.index(index=self.ES_INDEX, doc_type=self.ES_DOC, body=data, **kwargs)
            return True
        except Exception as err:
            raise err

    def get_es_data_by_id(self, es_id: str):
        """
        This method fetch the data from the es based on the id
        :param es_id:
        :return:
        """
        try:
            es_data = self.__es.get(index=self.ES_INDEX, id=es_id)
        except Exception as err:
            logging.error(err)
            es_data = {}
        return es_data
