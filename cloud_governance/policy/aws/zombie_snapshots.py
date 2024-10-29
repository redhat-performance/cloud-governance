from cloud_governance.common.utils.configs import HOURS_IN_MONTH
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class ZombieSnapshots(AWSPolicyOperations):
    """
    This class sends an alert mail for zombie snapshots ( AMI abandoned ) to the user after 4 days and delete after 7 days.
    """

    RESOURCE_ACTION = 'Delete'

    def __init__(self):
        super().__init__()
        self.__image_ids = self._get_ami_ids()

    def __snapshot_id_in_images(self, resource_id: str):
        """
        This method checks if snapshot_id exists in images list
        :param resource_id:
        :return:
        """
        image_snapshot_filter = {
            'Name': 'block-device-mapping.snapshot-id',
            'Values': [
                resource_id,
            ]
        }
        images = self._get_ami_ids(Filters=[image_snapshot_filter])
        return len(images) >= 1

    def run(self):
        """
        This method returns all the zombie snapshots and delete after x days
        @return:
        """
        monthly_price = self._resource_pricing.get_snapshot_unit_price(region_name=self._region)
        snapshots = self._ec2_operations.get_snapshots()
        zombie_snapshots = []
        for snapshot in snapshots:
            tags = snapshot.get('Tags', [])
            resource_id = snapshot.get('SnapshotId')
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_days = 0
            if not cluster_tag and not self.__snapshot_id_in_images(resource_id) and \
                    self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                unit_price = (monthly_price / HOURS_IN_MONTH) * float(snapshot.get('VolumeSize'))
                resource_data = self._get_es_schema(resource_id=resource_id,
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days, dry_run=self._dry_run,
                                                    name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                                                    region=self._region,
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    resource_type='Snapshot',
                                                    volume_size=f"{snapshot.get('VolumeSize')} GB",
                                                    unit_price=unit_price,
                                                    resource_state='Backup' if not cleanup_result else "Deleted"
                                                    )
                zombie_snapshots.append(resource_data)
                if not cleanup_result:
                    self.update_resource_tags(resource_id=resource_id, tags=tags + self.cost_savings_tag)
            else:
                cleanup_days = 0
                self.delete_resource_tags(resource_id=resource_id, tags=self.cost_savings_tag)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)
        return zombie_snapshots
