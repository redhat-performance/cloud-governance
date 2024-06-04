import datetime

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from tests.unittest.configs import ES_INDEX, TEST_INDEX_ID
from tests.unittest.mocks.elasticsearch.mock_elasticsearch import mock_elasticsearch


def test_missing_datetime():
    """
    This method test assert TypeError when we pass None as values
    @return:
    """
    es_operations = ElasticSearchOperations(es_host='localhost', es_port='9200')
    try:
        es_operations.delete_data_in_between_in_es(es_index='one', start_datetime=None, end_datetime=None)
        assert False
    except TypeError:
        assert TypeError


def test_missing_param_value():
    """
    This method test assert the Missing parameter when we didn't pass value
    @return:
    """
    es_operations = ElasticSearchOperations(es_host='localhost', es_port='9200')
    try:
        es_operations.delete_data_in_between_in_es(es_index='one', start_datetime=datetime.datetime.now())
        assert False
    except TypeError:
        assert TypeError


@mock_elasticsearch
def test_post_query():
    """
    This method tests the elasticsearch post query
    :return:
    :rtype:
    """
    es_index = ES_INDEX
    es_operations = ElasticSearchOperations(es_host='localhost', es_port='9200')
    # Upload data to es
    es_data = {
        'index-id': TEST_INDEX_ID,
        'test_type': 'Unittest',
    }
    es_operations.upload_to_elasticsearch(index=es_index, data=es_data)

    # fetch data
    query = {
        "query": {}
    }
    try:
        response = es_operations.post_query(es_index=es_index, query=query)
        assert response
    except TypeError:
        assert TypeError
