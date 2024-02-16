from azure.mgmt.network.models import NetworkInterface

from tests.unittest.mocks.azure.common_operations import CustomItemPaged
from tests.unittest.configs import SUB_ID, NETWORK_PROVIDER


class MockNetworkInterface(NetworkInterface):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get('virtual_machine'):
            self.virtual_machine = kwargs['virtual_machine']


class MockNetworkInterfaceOperations:

    NETWORK_INTERFACE = 'virtualNetworks'

    def __init__(self):
        super().__init__()
        self.__network_interfaces = {}

    def begin_create_or_update(self, network_interface_name: str, **kwargs):
        """
        This method creates the network interface
        :param network_interface_name:
        :type network_interface_name:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        network_interface_id = f'{SUB_ID}/{NETWORK_PROVIDER}/{self.NETWORK_INTERFACE}/{network_interface_name}'
        network_interface = MockNetworkInterface(network_interface_name=network_interface_name, id=network_interface_id,
                                                                                 **kwargs)
        self.__network_interfaces[network_interface_name] = network_interface
        return network_interface

    def list_all(self):
        """
        This method returns all the network interfaces
        :return:
        :rtype:
        """
        return CustomItemPaged(list(self.__network_interfaces.values()))
