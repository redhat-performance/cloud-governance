from azure.mgmt.network.models import PublicIPAddress

from tests.unittest.mocks.azure.common_operations import CustomItemPaged, Status
from tests.unittest.configs import SUB_ID, NETWORK_PROVIDER


class MockPublicIpAddress(PublicIPAddress):

    def __init__(self, name: str, tags: dict = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not tags:
            tags = {}
        self.name = name
        self.tags = tags
        if kwargs.get('ip_configuration'):
            self.ip_configuration = kwargs.get('ip_configuration')


class MockPublicIpAddressOperations:

    PUBLIC_IP_ADDRESS = 'publicIPAddresses'

    def __init__(self):
        self.__public_ipv4s = {}

    def begin_create_or_update(self, public_ip_address_name: str, **kwargs):
        """
        This method creates the public ipv4 address
        :param public_ip_address_name:
        :param kwargs:
        """
        public_ip_id = f'{SUB_ID}/{NETWORK_PROVIDER}/{self.PUBLIC_IP_ADDRESS}/{public_ip_address_name}'
        ip_address = MockPublicIpAddress(name=public_ip_address_name, id=public_ip_id,  **kwargs)
        self.__public_ipv4s[public_ip_address_name] = ip_address
        return ip_address

    def list_all(self):
        """
        This method list all public ips
        :return:
        :rtype:
        """
        return CustomItemPaged(resource_list=list(self.__public_ipv4s.values()))

    def begin_delete(self, resource_group_name: str, public_ip_address_name: str, **kwargs):
        """
        This method release the public ip
        :return:
        :rtype:
        """
        self.__public_ipv4s.pop(public_ip_address_name)
        deleted = False
        if public_ip_address_name not in self.__public_ipv4s:
            deleted = True
        return Status(deleted)
