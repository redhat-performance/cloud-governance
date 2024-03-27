from functools import wraps
from unittest.mock import patch

from azure.mgmt.network import NetworkManagementClient

from tests.unittest.mocks.azure.mock_network.mock_nat_gateway_operations import MockNatGatewayOperations
from tests.unittest.mocks.azure.mock_network.mock_network_interface_operations import MockNetworkInterfaceOperations
from tests.unittest.mocks.azure.mock_network.mock_public_ip_address_operations import MockPublicIpAddressOperations



def mock_network(method):
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
        with patch.object(NetworkManagementClient, 'public_ip_addresses', MockPublicIpAddressOperations()), \
             patch.object(NetworkManagementClient, 'network_interfaces', MockNetworkInterfaceOperations()), \
                patch.object(NetworkManagementClient, 'nat_gateways', MockNatGatewayOperations()):
            result = method(*args, **kwargs)
        return result

    return method_wrapper
