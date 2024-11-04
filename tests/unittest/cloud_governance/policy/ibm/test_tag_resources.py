from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.ibm.tag_resources import TagResources
from tests.unittest.mocks.ibm.mock_ibm_global_tagging import mock_ibm_global_tagging
from tests.unittest.mocks.ibm.mock_ibm_vpc import mock_ibm_vpc


@mock_ibm_global_tagging
@mock_ibm_vpc
def test_tag_all_vpc_resources():
    environment_variables.IBM_CLOUD_API_KEY = 'mock_ibm_api_key'
    environment_variables.RESOURCE_TO_TAG = 'virtual_servers'
    environment_variables.IBM_CUSTOM_TAGS_LIST = "cost-center: test"
    tag_resources = TagResources()
    res = tag_resources.tag_all_vpc_resources()
    assert res.get('messages').get('virtual_servers')
