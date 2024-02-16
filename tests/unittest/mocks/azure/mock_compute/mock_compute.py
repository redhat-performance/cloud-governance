from functools import wraps
from unittest.mock import patch

from azure.mgmt.compute import ComputeManagementClient

from tests.unittest.mocks.azure.mock_compute.mock_virtual_machines_operations import MockVirtualMachinesOperations
from tests.unittest.mocks.azure.mock_network.mock_public_ip_address_operations import MockPublicIpAddressOperations


def mock_compute(method):
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
        with patch.object(ComputeManagementClient, 'virtual_machines', MockVirtualMachinesOperations()):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
