# Tests that are not required benchmark-operator pod
import datetime
import time
from uuid import uuid4


from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from tests.integration.test_environment_variables import test_environment_variable

es = ElasticSearchOperations(es_host=test_environment_variable.get('elasticsearch', ''),
                             es_port=test_environment_variable.get('elasticsearch_port', ''))
es_index = 'test-cloud-governance-test-index'


def test_get_upload_update_elasticsearch():
    """
    This method test get upload and update elasticsearch
    @return:
    """

    if test_environment_variable['elasticsearch']:
        uuid = str(uuid4())
        # verify that data upload to elastic search
        data = {'tool': 'cloud-governance', 'uuid': uuid}
        es.upload_to_elasticsearch(index=es_index, data=data)
        assert es.verify_elasticsearch_data_uploaded(index=es_index, uuid=uuid)
        id = es.verify_elasticsearch_data_uploaded(index=es_index, uuid=uuid)
        es.update_elasticsearch_index(index=es_index, id=id[0],
                                      metadata={'cloud-governance_version': '1.0.324'})
        result = es.get_elasticsearch_index_by_id(index=es_index, id=id[0])
        assert result['_source']['uuid'] == uuid
        assert result['_source']['cloud-governance_version'] == '1.0.324'


def test_delete_data_between_range():
    """
    This method delete data in between range
    @return:
    """
    es.delete_data_in_es(es_index=es_index)
    data1 = {'Data': 'Test', 'timestamp': datetime.datetime.now() - datetime.timedelta(1)}
    es.upload_to_elasticsearch(index=es_index, data=data1)
    data2 = {'Data': 'Test2'}
    es.upload_to_elasticsearch(index=es_index, data=data2)
    time.sleep(3)
    end_time = datetime.datetime.now().replace(hour=0, minute=0, second=0)
    start_time = (end_time - datetime.timedelta(1)).replace(hour=0, minute=0, second=0)
    es.delete_data_in_between_in_es(es_index=es_index, start_datetime=start_time, end_datetime=end_time)
    start_time = end_time.replace(hour=0, minute=0, second=0)
    end_time = datetime.datetime.now()
    assert len(es.fetch_data_between_range(es_index=es_index, start_datetime=start_time, end_datetime=end_time)) == 1
    es.delete_data_in_es(es_index=es_index)


def test_fetch_data_between_range():
    """
    This method fetch the data from the es
    @return:
    """
    es.delete_data_in_es(es_index=es_index)
    data = {'Data': 'Test', 'timestamp': datetime.datetime.now() - datetime.timedelta(1)}
    es.upload_to_elasticsearch(index=es_index, data=data)
    time.sleep(3)
    end_time = datetime.datetime.now()
    start_time = (end_time - datetime.timedelta(1)).replace(hour=0, minute=0, second=0)
    assert len(es.fetch_data_between_range(es_index=es_index, start_datetime=start_time, end_datetime=end_time)) == 1
    es.delete_data_in_es(es_index=es_index)
    start_time = end_time - datetime.timedelta(1)
    assert len(es.fetch_data_between_range(es_index=es_index, start_datetime=start_time, end_datetime=end_time)) == 0
    es.delete_data_in_es(es_index=es_index)


def test_delete_data_in_elastic_search():
    """
    This method deletes the data in the elasticsearch
    @return:
    """
    es.delete_data_in_es(es_index=es_index)
    end_time = datetime.datetime.now().replace(hour=0, minute=0, second=0)
    start_time = (end_time - datetime.timedelta(1)).replace(hour=0, minute=0, second=0)
    assert len(es.fetch_data_between_range(es_index=es_index, start_datetime=start_time, end_datetime=end_time)) == 0
