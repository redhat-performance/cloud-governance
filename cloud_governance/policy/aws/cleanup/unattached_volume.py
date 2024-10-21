from cloud_governance.common.utils.configs import HOURS_IN_MONTH
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations
from cloud_governance.common.utils.utils import Utils


class UnattachedVolume(AWSPolicyOperations):
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
            tags = volume.get('Tags', [])
            resource_id = volume.get('VolumeId')
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=volume.get('Tags'))
            if Utils.equal_ignore_case(volume.get('State'), 'available') and \
                    cluster_tag not in active_cluster_ids and \
                    self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                monthly_price = self._resource_pricing.get_ebs_unit_price(region_name=self._region,
                                                                          ebs_type=volume.get('VolumeType', ''))
                unit_price = (monthly_price / HOURS_IN_MONTH) * float(volume.get('Size'))
                resource_data = self._get_es_schema(resource_id=resource_id,
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                    name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                                                    region=self._region,
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    resource_type=volume.get('VolumeType', ''),
                                                    unit_price=unit_price,
                                                    resource_state=volume.get(
                                                        'State') if not cleanup_result else "Deleted",
                                                    volume_size=f"{volume.get('Size')} GB"
                                                    )
                unattached_volumes.append(resource_data)
                if not cleanup_result:
                    self.update_resource_tags(resource_id=resource_id, tags=tags + self.cost_savings_tag)
            else:
                cleanup_days = 0
                self.delete_resource_tags(resource_id=resource_id, tags=self.cost_savings_tag)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)

        return unattached_volumes
