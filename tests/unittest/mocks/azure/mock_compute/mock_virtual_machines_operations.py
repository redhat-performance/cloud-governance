from azure.mgmt.compute.v2023_03_01.models import VirtualMachine, HardwareProfile

from tests.unittest.mocks.azure.common_operations import CustomItemPaged
from tests.unittest.configs import CURRENT_DATE, SUB_ID, COMPUTE_PROVIDER


class MockVirtualMachine(VirtualMachine):

    def __init__(self, vm_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name

        if not kwargs.get('time_created'):
            self.time_created = CURRENT_DATE.__str__()
        if not kwargs.get('hardware_profile'):
            self.hardware_profile = HardwareProfile(vm_size='Standard_D2s_v3')


class MockVirtualMachinesOperations:

    VIRTUAL_MACHINE = 'virtualMachines'

    def __init__(self):
        self.__virtual_machines = {}

    def begin_create_or_update(self, vm_name: str, **kwargs):
        """
        This method create or update the virtual_machine
        :param vm_name:
        :type vm_name:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        virtual_machine_id = f'{SUB_ID}/{COMPUTE_PROVIDER}/{self.VIRTUAL_MACHINE}/{vm_name}'
        self.__virtual_machines[vm_name] = MockVirtualMachine(vm_name=vm_name, id=virtual_machine_id, **kwargs)

    def list_all(self):
        """
        This method list all virtual machines
        :return:
        :rtype:
        """
        return CustomItemPaged(resource_list=list(self.__virtual_machines.values()))
