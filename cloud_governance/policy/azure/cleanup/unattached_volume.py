
from cloud_governance.policy.helpers.azure.azure_policy_operations import AzurePolicyOperations
from cloud_governance.common.utils.utils import Utils


class UnattachedVolume(AzurePolicyOperations):

    RESOURCE_ACTION = "Delete"

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the list of unattached volumes
        :return:
        :rtype:
        """
        unattached_volumes = []
        available_volumes = self._get_all_volumes()
        active_cluster_ids = self._get_active_cluster_ids()
        for volume in available_volumes:
            tags = volume.get('tags')
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            if Utils.equal_ignore_case(volume.get('disk_state'), 'Unattached') and cluster_tag not in active_cluster_ids:
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(
                    resource_id=volume.get('id'), tags=tags,
                    clean_up_days=cleanup_days)
                resource_data = self._get_es_schema(resource_id=volume.get('name'),
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                    name=volume.get('name'), region=volume.get('location'),
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    resource_type=f"{volume.get('sku', {}).get('tier')} "
                                                                  f"{volume.get('sku', {}).get('name')}",
                                                    resource_state=volume.get('disk_state') if not cleanup_result else "Deleted",
                                                    volume_size=f"{volume.get('disk_size_gb')} GB"
                                                    )
                unattached_volumes.append(resource_data)
            else:
                cleanup_days = 0
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=volume.get("id"), cleanup_days=cleanup_days, tags=tags)

        return unattached_volumes
