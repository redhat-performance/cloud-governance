from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieSnapshots(NonClusterZombiePolicy):

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
        zombie_snapshots = {}
        zombie_snapshots_data = []
        image_ids = self._get_ami_ids()
        for snapshot in snapshots:
            if snapshot.get('Description'):
                snapshot_images = self._get_image_ids_from_description(snapshot.get('Description'))
                found = False
                for snapshot_image in snapshot_images:
                    if snapshot_image in image_ids:
                        found = True
                if not found:
                    zombie_snapshots[snapshot.get('SnapshotId')] = snapshot.get('Tags')
                    zombie_snapshots_data.append([snapshot.get('SnapshotId'),
                                                  self._get_tag_name_from_tags(tags=snapshot.get('Tags')),
                                                  self._get_tag_name_from_tags(tags=snapshot.get('Tags'), tag_name='User'),
                                                  str(snapshot.get('VolumeSize')),
                                                  self._get_policy_value(tags=snapshot.get('Tags'))
                                                  ])
        if self._dry_run == "no":
            for zombie_id, tags in zombie_snapshots.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    self._ec2_client.delete_snapshot(SnapshotId=zombie_id)
                    logger.info(f'Snapshot is deleted {zombie_id}')
        return zombie_snapshots_data
