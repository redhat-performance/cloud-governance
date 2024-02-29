from azure.mgmt.network import NetworkManagementClient

from cloud_governance.common.clouds.azure.common.common_operations import CommonOperations
from cloud_governance.common.utils.utils import Utils


class NetworkOperations(CommonOperations):

    def __init__(self):
        super().__init__()
        self.__network_client = NetworkManagementClient(self._default_creds, subscription_id=self._subscription_id)

    def __get_all_public_ip_address(self):
        """
        This method returns all the Public address
        :return:
        :rtype:
        """
        ips = self.__network_client.public_ip_addresses.list_all()
        return self._item_paged_iterator(item_paged_object=ips, as_dict=True)

    def get_public_ipv4_addresses(self):
        """
        This method returns the Public IPV4
        :return:
        :rtype:
        """
        public_addresses = []
        for ipaddress in self.__get_all_public_ip_address():
            if Utils.equal_ignore_case(ipaddress.get('public_ip_address_version'), 'IPv4'):
                if Utils.equal_ignore_case(ipaddress.get('public_ip_allocation_method'), 'Static'):
                    public_addresses.append(ipaddress)
        return public_addresses

    def __get_network_interfaces(self):
        """
        This method returns the network interfaces
        :return:
        :rtype:
        """
        network_interfaces = self.__network_client.network_interfaces.list_all()
        network_interfaces = self._item_paged_iterator(item_paged_object=network_interfaces, as_dict=True)
        return network_interfaces

    def get_public_ipv4_network_interfaces(self):
        """
        This method returns the network interfaces have the public ip address attached
        :return:
        :rtype:
        """
        public_ipv4_network_interfaces = {}
        network_interfaces = self.__get_network_interfaces()
        for network_interface in network_interfaces:
            for ip_configuration in network_interface.get('ip_configurations', []):
                if ip_configuration.get('public_ip_address', {}):
                    public_ipv4_address_id = ip_configuration.get('public_ip_address', {}).get('id')
                    public_ipv4_network_interfaces.setdefault(public_ipv4_address_id, []).append(network_interface)
        return public_ipv4_network_interfaces

    # delete operations
    def release_public_ip(self, resource_id: str):
        """
        This method releases the public ip
        :return:
        :rtype:
        """
        id_key_pairs = self.get_id_dict_data(resource_id)
        resource_group_name = id_key_pairs.get('resourcegroups')
        public_ip_address_name = id_key_pairs.get('publicipaddresses')
        status = self.__network_client.public_ip_addresses.begin_delete(resource_group_name=resource_group_name,
                                                                        public_ip_address_name=public_ip_address_name)
        return status.done()
