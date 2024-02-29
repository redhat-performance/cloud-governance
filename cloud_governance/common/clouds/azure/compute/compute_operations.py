from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.v2023_03_01.models import VirtualMachine

from cloud_governance.common.clouds.azure.common.common_operations import CommonOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class ComputeOperations(CommonOperations):

    def __init__(self):
        super().__init__()
        self.__compute_client = ComputeManagementClient(self._default_creds, subscription_id=self._subscription_id)

    @logger_time_stamp
    def get_instances_by_resource_group(self, resource_group_name: str) -> [VirtualMachine]:
        """
        This method returns all the compute resources by resource group
        :return:
        """
        instances_paged_object = self.__compute_client.virtual_machines.list(resource_group_name=resource_group_name)
        instances_list: [VirtualMachine] = self._item_paged_iterator(item_paged_object=instances_paged_object)
        return instances_list

    def get_all_instances(self) -> [VirtualMachine]:
        """
        This method returns all the virtual machines
        :return:
        :rtype:
        """
        instances_paged_object = self.__compute_client.virtual_machines.list_all()
        instances_list: [VirtualMachine] = self._item_paged_iterator(item_paged_object=instances_paged_object)
        return instances_list

    def get_instance_statuses(self, resource_id: str, vm_name: str) -> dict:
        """
        This method returns the virtual machine instance status
        :param vm_name:
        :type vm_name:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        resource_group_name = self.get_resource_group_name_from_resource_id(resource_id=resource_id)
        virtual_machine = self.__compute_client.virtual_machines.instance_view(resource_group_name=resource_group_name,
                                                                               vm_name=vm_name)
        return virtual_machine.as_dict()

    def stop_vm(self, resource_id: str):
        """
        This method stops the vm
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        id_key_pairs = self.get_id_dict_data(resource_id)
        resource_group_name = id_key_pairs.get('resourcegroups')
        vm_name = id_key_pairs.get('virtualmachines')
        status = self.__compute_client.virtual_machines.begin_deallocate(resource_group_name=resource_group_name,
                                                                         vm_name=vm_name)
        return status.done()

    # volumes -> disks
    def get_all_disks(self):
        """
        This method returns all the disks
        :return:
        :rtype:
        """
        paged_volumes = self.__compute_client.disks.list()
        return self._item_paged_iterator(item_paged_object=paged_volumes, as_dict=True)

    def delete_disk(self, resource_id: str):
        """
        This method deletes the disk
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        id_key_pairs = self.get_id_dict_data(resource_id)
        resource_group_name = id_key_pairs.get('resourcegroups')
        disk_name = id_key_pairs.get('disks')
        status = self.__compute_client.disks.begin_delete(resource_group_name=resource_group_name, disk_name=disk_name)
        return status.done()
