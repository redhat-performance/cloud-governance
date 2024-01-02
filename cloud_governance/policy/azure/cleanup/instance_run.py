from cloud_governance.common.helpers.azure.azure_policy_operations import AzurePolicyOperations
from cloud_governance.policy.abstract_policies.cleanup.abstractinstance_run import AbstractInstanceRun


class InstanceRun(AbstractInstanceRun, AzurePolicyOperations):

    def __init__(self):
        super().__init__()

    def _update_instance_type_count(self):
        """
        This method returns the instance type count by region
        :return: { region : {instance_type: instance_count} }
        :rtype: dict
        """
        resources = self._get_al_instances()
        instance_types = {}
        for resource in resources:
            vm_type = resource.hardware_profile.vm_size
            region = resource.location
            instance_types.setdefault(region, {}).update(
                {vm_type: instance_types.get(region).get(vm_type, 0) + 1}
            )
        return instance_types

    def __get_instance_status(self, resource_id: str, vm_name: str):
        """
        This method returns the VM status of the Virtual Machine
        :param resource_id:
        :type resource_id:
        :param vm_name:
        :type vm_name:
        :return:
        :rtype:
        """
        instance_statuses = self.compute_operations.get_instance_statuses(resource_id=resource_id, vm_name=vm_name)
        statuses = instance_statuses.get('statuses', {})
        if len(statuses) >= 2:
            status = statuses[1].get('display_status', '').lower()
        elif len(statuses) == 1:
            status = statuses[0].get('display_status', '').lower()
        else:
            status = 'Unknown Status'
        return status

    def _instance_run(self):
        """
        This method returns the running vms in the AAzure cloud and stops based on the action
        :return:
        :rtype:
        """
        vms_list = self._get_al_instances()
        running_vms = []
        for vm in vms_list:
            status = self.__get_instance_status(resource_id=vm.id, vm_name=vm.name)
            tags = vm.tags if vm.tags else {}
            if 'running' in status:
                running_days = self.calculate_days(vm.time_created)
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=vm.id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                resource_data = self._get_es_data_schema_format(
                    resource_id=vm.name,
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=vm.time_created,
                    instance_type=vm.hardware_profile.vm_size,
                    instance_state=status if cleanup_result else 'Vm Stopped',
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=vm.name,
                    region=vm.location, cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name
                )
                if self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_vms.append(resource_data)
            else:
                cleanup_days = 0
            self.update_resource_day_count_tag(resource_id=vm.id, cleanup_days=cleanup_days, tags=tags)
        return running_vms
