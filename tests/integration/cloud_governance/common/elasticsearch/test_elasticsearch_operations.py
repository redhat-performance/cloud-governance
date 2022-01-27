# Tests that are not required benchmark-operator pod
from uuid import uuid4

import pytest

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from tests.integration.cloud_governance.test_environment_variables import *


@pytest.mark.skip(reason="No elasticsearch for test")
def test_get_upload_update_es():
    """
    This method test get upload and update elasticsearch
    @return:
    """

    if test_environment_variable['elasticsearch']:
        uuid = str(uuid4())
        # verify that data upload to elastic search
        es = ElasticSearchOperations(es_host=test_environment_variable.get('elasticsearch', ''),
                                     es_port=test_environment_variable.get('elasticsearch_port', ''))
        data = {'tool': 'cloud-governance', 'uuid': uuid}
        es.upload_to_es(index='cloud-governance-test', data=data)
        assert es.verify_es_data_uploaded(index='cloud-governance-test', uuid=uuid)
        id = es.verify_es_data_uploaded(index='cloud-governance-test', uuid=uuid)
        es.update_es_index(index='cloud-governance-test', id=id[0], metadata={'cloud-governance_version': '1.0.324'})
        result = es.get_es_index_by_id(index='cloud-governance-test', id=id[0])
        assert result['_source']['uuid'] == uuid
        assert result['_source']['cloud-governance_version'] == '1.0.324'


