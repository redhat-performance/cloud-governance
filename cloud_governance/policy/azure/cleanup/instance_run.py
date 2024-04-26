from datetime import datetime

from cloud_governance.policy.helpers.azure.azure_policy_operations import AzurePolicyOperations


class InstanceRun(AzurePolicyOperations):

    INSTANCE_TYPES_ES_INDEX = "cloud-governance-instance-types"
    RESOURCE_ACTION = "Stopped"

    def __init__(self):
        super().__init__()

    def _upload_instance_type_count_to_elastic_search(self):
        """
        This method uploads the instance type count to elasticsearch
        :return:
        :rtype:
        """
        instance_types = self._update_instance_type_count()
        account = self.account
        current_day = datetime.utcnow()
        es_instance_types_data = []
        for region, instance_types in instance_types.items():
            for instance_type, instance_type_count in instance_types.items():
                es_instance_types_data.append({
                    'instance_type': instance_type,
                    'instance_count': instance_type_count,
                    'timestamp': current_day,
                    'region': region,
                    'account': account,
                    'PublicCloud': self._cloud_name,
                    'index_id': f'{instance_type}-{self._cloud_name.lower()}-{account.lower()}-{region}-{str(current_day.date())}'
                })
        self._es_upload.es_upload_data(items=es_instance_types_data, es_index=self.INSTANCE_TYPES_ES_INDEX,
                                       set_index='index_id')

    def _update_instance_type_count(self):
        """
        This method returns the instance type count by region
        :return: { region : {instance_type: instance_count} }
        :rtype: dict
        """
        resources = self._get_all_instances()
        instance_types = {}
        for resource in resources:
            vm_type = resource.hardware_profile.vm_size
            region = resource.location
            instance_types.setdefault(region, {}).update(
                {vm_type: instance_types.get(region).get(vm_type, 0) + 1}
            )
        return instance_types

    def run_policy_operations(self):
        """
        This method returns the running vms in the AAzure cloud and stops based on the action
        :return:
        :rtype:
        """
        self._upload_instance_type_count_to_elastic_search()
        vms_list = self._get_all_instances()
        running_vms = []
        for vm in vms_list:
            status = self._get_instance_status(resource_id=vm.id, vm_name=vm.name)
            tags = vm.tags if vm.tags else {}
            cleanup_result = False
            if 'running' in status:
                running_days = self.calculate_days(vm.time_created)
                if self._shutdown_period:
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(resource_id=vm.id, tags=tags,
                                                                     clean_up_days=cleanup_days)
                else:
                    cleanup_days = 0
                resource_data = self._get_es_schema(
                    resource_id=vm.name,
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=vm.time_created,
                    resource_type=vm.hardware_profile.vm_size,
                    resource_state=status if not cleanup_result else 'Vm Stopped',
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=vm.name,
                    resource_action=self.RESOURCE_ACTION,
                    region=vm.location, cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name
                )
                if self._shutdown_period and self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_vms.append(resource_data)
            else:
                cleanup_days = 0
            if self._shutdown_period:
                self.update_resource_day_count_tag(resource_id=vm.id, cleanup_days=cleanup_days, tags=tags)
        return running_vms
