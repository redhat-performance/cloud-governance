import uuid
from datetime import datetime

from azure.mgmt.compute.v2023_01_02.models import Disk, DiskSku
from azure.mgmt.compute.v2023_03_01.models import VirtualMachine, HardwareProfile, VirtualMachineInstanceView, \
    InstanceViewStatus

from tests.unittest.mocks.azure.common_operations import CustomItemPaged


class MockVirtualMachine(VirtualMachine):

    def __init__(self, tags: dict = None):
        super().__init__(location='mock')
        self.tags = tags if tags else {}
        self.name = 'mock_machine'
        self.time_created = datetime.utcnow()
        self.hardware_profile = HardwareProfile(vm_size='Standard_D2s_v3')
        self.id = f'/subscriptions/{uuid.uuid1()}/resourceGroups/mock/providers/Microsoft.Compute/virtualMachines/mock-machine'


class MockDisk(Disk):

    def __init__(self, disk_state: str, disk_size_gb: int,  tags: dict = {}, location: str = 'mock', **kwargs: any):
        super().__init__(location=location)
        self.tags = tags if tags else {}
        self.name = 'mock_disk'
        self.sku = DiskSku(name='Standard_LRS', tier='Standard')
        self.disk_state = disk_state
        self.disk_size_gb = disk_size_gb


class MockVirtualMachineInstanceView(VirtualMachineInstanceView):

    def __init__(self, status1: str = "Unknown", status2: str = 'Vm Running'):
        super().__init__()
        self.statuses = [
            InstanceViewStatus(display_status=status1),
            InstanceViewStatus(display_status=status2)
        ]


class MockAzure:

    def __init__(self, vms: list = None, disks: list = None, status1: str = "Unknown", status2: str = 'Vm Running'):
        self.vms = vms if vms else []
        self.status1 = status1
        self.status2 = status2
        self.disks = disks if disks else []

    def mock_list_all(self, *args, **kwargs):
        return CustomItemPaged(resource_list=self.vms)

    def mock_instance_view(self, *args, **kwargs):
        return MockVirtualMachineInstanceView(status1=self.status1, status2=self.status2)

    def mock_list_disks(self, *args, **kwargs):
        return CustomItemPaged(resource_list=self.disks)
