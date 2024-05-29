from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class ZombieSnapshots(AWSPolicyOperations):
    """
    This class sends an alert mail for zombie snapshots ( AMI abandoned ) to the user after 4 days and delete after 7 days.
    """

    RESOURCE_ACTION = 'Delete'

    def __init__(self):
        super().__init__()
        self.__image_ids = self._get_ami_ids()

    def __get_image_ids_from_description(self, snapshot_description: str):
        """
        This method gets image Ids from snapshot description
        Two cases:
        # Created by CreateImage(i-******) for ami-********
        # Copied for DestinationAmi ami-******* from SourceAmi ami-******* for SourceSnapshot snap-******. Task created on 1,566,308,778,174.
        @return:
        """
        image_ids = []
        images_array = snapshot_description.split('ami-')[1:]
        for image in images_array:
            image_ids.append(f'ami-{image.split(" ")[0]}')
        return image_ids

    def __is_zombie_snapshot(self, snapshot_description: str):
        """
        This method returns bool on verifying snapshots as zombie or not
        :param snapshot_description:
        :return:
        """
        zombie_snapshot = True
        if snapshot_description:
            snapshot_images = self.__get_image_ids_from_description(snapshot_description)
            for snapshot_image in snapshot_images:
                if snapshot_image in self.__image_ids:
                    return False
        return zombie_snapshot

    def run(self):
        """
        This method returns all the zombie snapshots and delete after x days
        @return:
        """
        snapshots = self._ec2_operations.get_snapshots()
        zombie_snapshots = []
        for snapshot in snapshots:
            tags = snapshot.get('Tags', [])
            resource_id = snapshot.get('SnapshotId')
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_days = 0
            if not cluster_tag and self.__is_zombie_snapshot(snapshot.get('Description')):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=resource_id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                unit_price = 0
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
                                                    unit_price=unit_price, resource_state='Backup' if not cleanup_result else "Deleted"
                                                    )
                zombie_snapshots.append(resource_data)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=resource_id, cleanup_days=cleanup_days, tags=tags)
        return zombie_snapshots
