from azure.mgmt.network.models import NatGateway

from tests.unittest.configs import NETWORK_PROVIDER, SUB_ID
from tests.unittest.mocks.azure.common_operations import CustomItemPaged


class MockNatGateway(NatGateway):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provisioning_state = kwargs.get('provisioning_state')


class MockNatGatewayOperations:

    NAT_GATEWAY = 'virtualNetworks'

    def __init__(self):
        self.__nat_gateways = {}

    def begin_create_or_update(self, nat_gateway_name: str, location: str = 'eastus',
                               provisioning_state: str = 'Succeed', **kwargs):
        """
        This method creates the nat gateway resource
        :param provisioning_state:
        :type provisioning_state:
        :param location:
        :type location:
        :param nat_gateway_name:
        :type nat_gateway_name:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        nat_gateway_id = f'{SUB_ID}/{NETWORK_PROVIDER}/{self.NAT_GATEWAY}/{nat_gateway_name}'
        nat_gateway = MockNatGateway(id=nat_gateway_id, name=nat_gateway_name, location=location,
                                     provisioning_state=provisioning_state, **kwargs)
        self.__nat_gateways[nat_gateway_name] = nat_gateway
        return nat_gateway

    def list_all(self):
        """
        This method returns all the network interfaces
        :return:
        :rtype:
        """
        return CustomItemPaged(list(self.__nat_gateways.values()))
