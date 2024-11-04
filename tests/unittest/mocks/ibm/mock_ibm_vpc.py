from unittest.mock import patch
import ibm_vpc
from ibm_cloud_sdk_core import DetailedResponse


class MockDetailedResponse(DetailedResponse):

    def __init__(self, response):
        super().__init__()
        self.result = response


class MockVpcV1(ibm_vpc.vpc_v1.VpcV1):

    def __init__(self, *args, **kwargs):
        self.regions = [{
            'endpoint': 'https://au-syd.iaas.cloud.ibm.com',
            'href': 'https://us-south.iaas.cloud.ibm.com/v1/regions/au-syd',
            'name': 'au-syd',
            'status': 'available'
        }]
        self.instances = [{
            'crn': 'id123',
            'name': 'test-mock-vm'
        }]

    def set_region(self, region: dict):
        """
        This method set region
        :param region:
        :return:
        """
        self.regions.append(region)

    def list_regions(self, *args, **kwargs) -> MockDetailedResponse:
        response = {
            'regions': self.regions
        }
        return MockDetailedResponse(response)

    def list_instances(self, *args, **kwargs) -> MockDetailedResponse:
        response = {
            'instances': self.instances
        }
        return MockDetailedResponse(response)


def mock_ibm_vpc(method):
    def method_wrapper(*args, **kwargs):
        """
        This is the wrapper method to wraps the method inside the function
        @param args:
        @param kwargs:
        @return:
        """
        with patch.object(ibm_vpc.vpc_v1, 'VpcV1', MockVpcV1):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
