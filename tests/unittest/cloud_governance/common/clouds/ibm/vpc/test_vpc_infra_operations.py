from cloud_governance.common.clouds.ibm.vpc.vpc_infra_operations import VpcInfraOperations
from cloud_governance.main.environment_variables import environment_variables
from tests.unittest.mocks.ibm.mock_ibm_vpc import mock_ibm_vpc

environment_variables.IBM_CLOUD_API_KEY = 'mock_ibm_api_key'


@mock_ibm_vpc
def test_get_regions():
    """
    This test checks that the get_regions function works.
    :return:
    """
    vpc_infra_operations = VpcInfraOperations()
    response = vpc_infra_operations.get_regions()
    assert response is not None
    assert len(response) == 1


@mock_ibm_vpc
def test_get_instances():
    """
    This test checks that the get_instances function works.
    :return:
    """
    vpc_infra_operations = VpcInfraOperations()
    response = vpc_infra_operations.get_instances()
    assert response is not None
    assert len(response) == 1
