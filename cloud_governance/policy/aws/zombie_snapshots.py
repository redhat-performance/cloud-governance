from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieSnapshots(NonClusterZombiePolicy):
    """
    This class sends an alert mail for zombie snapshots ( AMI abandoned ) to the user after 4 days and delete after 7 days.
    """

    def __init__(self):
        super().__init__()

    def _get_image_ids_from_description(self, snapshot_description: str):
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

    def run(self):
        """
        This method return all the zombie snapshots, delete if dry_run no
        @return:
        """
        snapshots = self._ec2_operations.get_snapshots()
        zombie_snapshots = []
        image_ids = self._get_ami_ids()
        for snapshot in snapshots:
            if not self._check_cluster_tag(tags=snapshot.get('Tags')):
                if snapshot.get('Description'):
                    snapshot_images = self._get_image_ids_from_description(snapshot.get('Description'))
                    tags = snapshot.get('Tags')
                    found = False
                    for snapshot_image in snapshot_images:
                        if snapshot_image in image_ids:
                            found = True
                    snapshot_id = snapshot.get('SnapshotId')
                    if not found:
                        unused_days = self._get_resource_last_used_days(tags=tags)
                        zombie_snapshot = self._check_resource_and_delete(resource_name='Snapshot',
                                                                          resource_id='SnapshotId',
                                                                          resource_type='CreateSnapshot',
                                                                          resource=snapshot,
                                                                          empty_days=unused_days,
                                                                          days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE,
                                                                          tags=tags)
                        if zombie_snapshot:
                            zombie_snapshots.append([snapshot.get('SnapshotId'),
                                                     self._get_tag_name_from_tags(tags=tags),
                                                     self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                     f'{str(snapshot.get("VolumeSize"))}Gb',
                                                     self._get_policy_value(tags=snapshot.get('Tags')), str(unused_days)
                                                     ])
                    else:
                        unused_days = 0
                    self._update_resource_tags(resource_id=snapshot_id, tags=tags, left_out_days=unused_days,
                                               resource_left_out=not found)
        return zombie_snapshots
