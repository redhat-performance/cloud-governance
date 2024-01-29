
from cloud_governance.common.clouds.azure.compute.compute_operations import ComputeOperations
from cloud_governance.common.clouds.azure.compute.resource_group_operations import ResourceGroupOperations
from cloud_governance.policy.helpers.abstract_policy_operations import AbstractPolicyOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.utils import Utils


class AzurePolicyOperations(AbstractPolicyOperations):

    def __init__(self):
        self._cloud_name = 'Azure'
        self.compute_operations = ComputeOperations()
        self.resource_group_operations = ResourceGroupOperations()
        super().__init__()

    def get_tag_name_from_tags(self, tags: dict, tag_name: str):
        """
        This method returns the tag value by the tag_name
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :return:
        :rtype:
        """
        if tags:
            for key, value in tags.items():
                if Utils.equal_ignore_case(key, tag_name):
                    return value
        return ''

    def _delete_resource(self, resource_id: str):
        """
        This method deletes the
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        action = "deleted"
        try:
            if self._policy == 'instance_run':
                action = "Stopped"
                self.compute_operations.stop_vm(resource_id=resource_id)
            elif self._policy == 'unattached_volume':
                self.compute_operations.delete_disk(resource_id=resource_id)
            logger.info(f'{self._policy} {action}: {resource_id}')
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def update_resource_day_count_tag(self, resource_id: str, cleanup_days: int, tags: dict):
        tags = self._update_tag_value(tags=tags, tag_name='DaysCount', tag_value=str(cleanup_days))
        try:
            if self._policy in ['instance_run', 'unattached_volume']:
                self.resource_group_operations.creates_or_updates_tags(resource_id=resource_id, tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def _update_tag_value(self, tags: dict, tag_name: str, tag_value: str):
        """
        This method returns the updated tag_list by adding the tag_name and tag_value to the tags
        @param tags:
        @param tag_name:
        @param tag_value:
        @return:
        """
        if not tags:
            tags = {}
        if self._dry_run == "yes":
            tag_value = 0
        tag_value = f'{self.CURRENT_DATE}@{tag_value}'
        found = False
        updated_tags = {}
        if tags:
            for key, value in tags.items():
                if Utils.equal_ignore_case(key, tag_name):
                    if value.split("@")[0] != self.CURRENT_DATE:
                        updated_tags[key] = tag_value
                    else:
                        if int(tag_value.split("@")[-1]) == 0 or int(tag_value.split("@")[-1]) == 1:
                            updated_tags[key] = tag_value
                    found = True
        tags.update(updated_tags)
        if not found:
            tags.update({tag_name: tag_value})
        return tags

    def _get_all_instances(self):
        """
        This method returns the all instances list
        :return:
        :rtype:
        """
        return self.compute_operations.get_all_instances()

    def run_policy_operations(self):
        raise NotImplementedError("This method needs to be implemented")

    def _get_all_volumes(self) -> list:
        """
        This method returns the volumes by state
        :return:
        :rtype:
        """
        volumes = self.compute_operations.get_all_disks()
        return volumes
