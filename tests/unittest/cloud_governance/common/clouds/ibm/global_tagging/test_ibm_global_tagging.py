from cloud_governance.common.clouds.ibm.tagging.global_tagging_operations import GlobalTaggingOperations
from cloud_governance.main.environment_variables import environment_variables
from tests.unittest.mocks.ibm.mock_ibm_global_tagging import mock_ibm_global_tagging

environment_variables.IBM_CLOUD_API_KEY = 'mock_ibm_api_key'
environment_variables.IBM_ACCOUNT_ID = "test"


@mock_ibm_global_tagging
def test_update_tags():
    """
    This method tests the update_tags function of GlobalTagging Operations of IBM Cloud
    :return:
    """
    global_tagging_operations = GlobalTaggingOperations()
    crns = ['id123']
    tags = ["cost-center: test"]
    response = global_tagging_operations.update_tags(resources_crn=crns, tags=tags)
    assert response[0]
