from azure.mgmt.compute.v2023_03_01.models import VirtualMachine, HardwareProfile, VirtualMachineInstanceView, \
    InstanceViewStatus

from tests.unittest.mocks.azure.common_operations import CustomItemPaged
from tests.unittest.configs import SUB_ID, COMPUTE_PROVIDER, CURRENT_DATE_TIME


class MockVirtualMachine(VirtualMachine):

    def __init__(self, vm_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.id = kwargs.get('id')

        if not kwargs.get('time_created'):
            self.time_created = CURRENT_DATE_TIME
        else:
            self.time_created = kwargs.get('time_created')
        if not kwargs.get('hardware_profile'):
            self.hardware_profile = HardwareProfile(vm_size='Standard_D2s_v3')
        else:
            self.hardware_profile = kwargs.get('hardware_profile')


class MockVirtualMachinesOperations:
    VIRTUAL_MACHINE = 'virtualMachines'

    def __init__(self):
        self.__virtual_machines = {}
        self.__instance_views = {}

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
        virtual_machine = MockVirtualMachine(vm_name=vm_name, id=virtual_machine_id, **kwargs)
        self.__virtual_machines[vm_name] = virtual_machine
        return virtual_machine

    def list_all(self):
        """
        This method list all virtual machines
        :return:
        :rtype:
        """
        return CustomItemPaged(resource_list=list(self.__virtual_machines.values()))

    def instance_view(self, resource_group_name: str, vm_name: str, **kwargs):
        """
        This method returns the instance view status
        :return:
        :rtype:
        """
        instance_view = MockVirtualMachineInstanceView(**kwargs)
        self.__instance_views[vm_name] = instance_view
        return instance_view


class MockVirtualMachineInstanceView(VirtualMachineInstanceView):

    def __init__(self, status1: str = "Unknown", status2: str = 'Vm Running'):
        super().__init__()
        self.statuses = [
            InstanceViewStatus(display_status=status1),
            InstanceViewStatus(display_status=status2)
        ]
