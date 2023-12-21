import uuid
from datetime import datetime

from azure.core.paging import ItemPaged
from azure.mgmt.compute.v2023_03_01.models import VirtualMachine, HardwareProfile, VirtualMachineInstanceView, \
    InstanceViewStatus


class MockVirtualMachine(VirtualMachine):

    def __init__(self, tags: dict = None):
        super().__init__(location='mock')
        self.tags = tags if tags else {}
        self.name = 'mock_machine'
        self.time_created = datetime.utcnow()
        self.hardware_profile = HardwareProfile(vm_size='Standard_D2s_v3')
        self.id = f'/subscriptions/{uuid.uuid1()}/resourceGroups/mock/providers/Microsoft.Compute/virtualMachines/mock-machine'


class MockVirtualMachineInstanceView(VirtualMachineInstanceView):

    def __init__(self, status1: str = "Unknown", status2: str = 'Vm Running'):
        super().__init__()
        self.statuses = [
            InstanceViewStatus(display_status=status1),
            InstanceViewStatus(display_status=status2)
        ]


class CustomItemPaged(ItemPaged):

    def __init__(self, vms_list: list = None):
        super().__init__()
        self._page_iterator = iter(vms_list if vms_list else [])


class MockAzure:

    def __init__(self, vms: list = None, status1: str = "Unknown", status2: str = 'Vm Running'):
        self.vms = vms if vms else []
        self.status1 = status1
        self.status2 = status2

    def mock_list_all(self, *args, **kwargs):
        return CustomItemPaged(vms_list=self.vms)

    def mock_instance_view(self, *args, **kwargs):
        return MockVirtualMachineInstanceView(status1=self.status1, status2=self.status2)
