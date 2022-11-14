import datetime

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations


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


