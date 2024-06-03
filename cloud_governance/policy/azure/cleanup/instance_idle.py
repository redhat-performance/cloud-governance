
from cloud_governance.common.utils.configs import INSTANCE_IDLE_DAYS
from cloud_governance.common.utils.utils import Utils
from cloud_governance.policy.helpers.azure.azure_policy_operations import AzurePolicyOperations


class InstanceIdle(AzurePolicyOperations):
    """
    This class stop the idle instances more than 4 days if it matches the required metrics
    CpuUtilization < 2 percent
    NetworkIN < 5k bytes
    NetworkOut < 5k bytes
    We trigger email if the instance is idle 2 days and stop the instance if it is idle 4 days
    """

    RESOURCE_ACTION = "Stop"

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the running instances
        :return:
        :rtype:
        """
        vms_list = self._get_all_instances()
        running_vms = []
        for vm in vms_list:
            vm = vm.as_dict()
            status = self._get_instance_status(resource_id=vm.get("id"), vm_name=vm.get("name"))
            tags = vm.get("tags") if vm.get("tags", {}) else {}
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_result = False
            running_days = self.calculate_days(vm.get("time_created"))
            if Utils.contains_ignore_case(string=status, str1='running') and not cluster_tag and \
                    Utils.greater_than(val1=running_days, val2=INSTANCE_IDLE_DAYS) and \
                    self.verify_instance_idle(resource_id=vm.get("id")):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=vm.get("id"), tags=tags,
                                                                 clean_up_days=cleanup_days)
                resource_data = self._get_es_schema(
                    resource_id=vm.get("name"),
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=vm.get("time_created"),
                    resource_type=vm.get("hardware_profile", {}).get("vm_size"),
                    resource_state=status if not cleanup_result else 'Vm Stopped',
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=vm.get("name"),
                    resource_action=self.RESOURCE_ACTION,
                    region=vm.get("location"), cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name
                )
                if self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_vms.append(resource_data)
            else:
                cleanup_days = 0
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=vm.get("id"), cleanup_days=cleanup_days,
                                                   tags=tags)
        return running_vms
