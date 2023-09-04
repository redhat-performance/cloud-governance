from azure.mgmt.compute import ComputeManagementClient

from cloud_governance.common.clouds.azure.compute.common_operations import CommonOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class ComputeOperations(CommonOperations):

    def __init__(self):
        super().__init__()
        self.__compute_client = ComputeManagementClient(self._default_creds, subscription_id=self._subscription_id)

    @logger_time_stamp
    def get_instances_by_resource_group(self, resource_group_name: str):
        """
        This method returns all the compute resources by resource group
        :return:
        """
        instances_paged_object = self.__compute_client.virtual_machines.list(resource_group_name=resource_group_name)
        instances_list = self._item_paged_iterator(item_paged_object=instances_paged_object)
        return instances_list

