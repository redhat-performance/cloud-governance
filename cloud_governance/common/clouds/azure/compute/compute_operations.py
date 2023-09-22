from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.v2023_03_01.models import VirtualMachine

from cloud_governance.common.clouds.azure.compute.common_operations import CommonOperations
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

    def get_instance_data(self, resource_id: str, vm_name: str) -> VirtualMachine:
        """
        This method returns the virtual machine data by taking the id
        :param vm_name:
        :type vm_name:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        resource_group_name = self._get_resource_group_name_from_resource_id(resource_id=resource_id)
        virtual_machine = self.__compute_client.virtual_machines.get(resource_group_name=resource_group_name,
                                                                     vm_name=vm_name)
        return virtual_machine
