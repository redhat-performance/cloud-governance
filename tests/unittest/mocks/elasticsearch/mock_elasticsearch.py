import uuid
from functools import wraps
from unittest.mock import patch

from elasticsearch import Elasticsearch


class MockElasticsearch:

    def __init__(self):
        self.__es_data = {}

    def index(self, index: str, body: str, **kwargs):
        id = kwargs.get('id', uuid.uuid1())
        self.__es_data.setdefault(index, {}).setdefault(id, body)
        return True

    def search(self, index: str, body: dict, **kwargs):
        response = self.__es_data.get(index)
        if response:
            return {
                'hits': {
                    'hits': response
                }
            }
        return {'hits': {
            'hits': {}
        }}


def mock_elasticsearch(method):
    """
    This method is mocking for Jira class methods which are used in Jira Operations    @param method:
    @return:
    """

    @wraps(method)
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        mock_class = MockElasticsearch()
        with patch.object(Elasticsearch, 'index', mock_class.index), \
             patch.object(Elasticsearch, 'search', mock_class.search):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
