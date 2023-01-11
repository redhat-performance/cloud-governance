from datetime import datetime

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_operations.aws.tag_non_cluster.non_cluster_operations import NonClusterOperations


class RemoveNonClusterTags(NonClusterOperations):

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes', input_tags: dict = ''):
        super().__init__(region=region, dry_run=dry_run, input_tags=input_tags)

    def __get_instance_tags(self, launch_time: datetime, instance_id: str, tags: list):
        """
        This method returns the tags to update  the instance tags
        @param launch_time:
        @param instance_id:
        @param tags:
        @return:
        """
        username = self._get_username_from_cloudtrail(start_time=launch_time, resource_id=instance_id, resource_type='AWS::EC2::Instance')
        search_tags = []
        user_tags = self.iam_client.get_user_tags(username=username)
        if not username:
            search_tags.extend(self._fill_na_tags())
        else:
            search_tags.append(self._build_tag(key='Email', value=f'{username}@redhat.com'))
        search_tags.append(self._build_tag(key='LaunchTime', value=launch_time))
        search_tags.extend(self._append_input_tags())
        search_tags.extend(user_tags)
        return search_tags

    def non_cluster_update_ec2(self, instances_list: list = None):
        """
        This method removes the tags of ec2 instances
        @return:
        """
        if not instances_list:
            instances_list = self._get_resource_data(resource_method=self._get_instances_data)
        instances_ids = []
        for instance in instances_list:
            for item in instance:
                instance_id = item.get('InstanceId')
                launch_time = item.get('LaunchTime')
                add_tags = self.__get_instance_tags(launch_time=launch_time, instance_id=instance_id, tags=item.get('Tags'))
                if add_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.delete_tags(Resources=[instance_id], Tags=add_tags)
                        logger.info(f'Delete tags of instance: {instance_id} total: {len(add_tags)} tags: {add_tags}')
                    instances_ids.append(instance_id)
        logger.info(f'non_cluster_ec2 count: {len(sorted(instances_ids))} {sorted(instances_ids)}')
        return sorted(instances_ids)

    def update_volumes(self, volumes_data: list = None):
        """
        This method removes the tags of non-cluster volumes
        @param volumes_data:
        @return:
        """
        if not volumes_data:
            volumes_data = self._get_resource_data(resource_method=self.ec2_operations.get_volumes)
        volume_ids = []
        for volume in volumes_data:
            volume_id = volume.get('VolumeId')
            tag_name = ''
            username = self._get_username_from_cloudtrail(start_time=volume.get('CreateTime'), resource_id=volume_id, resource_type='AWS::EC2::Volume')
            search_tags = []
            if not username:
                get_tags, username = self._get_tags_fom_attachments(attachments=volume.get('Attachments'))
                search_tags.extend(get_tags)
            else:
                search_tags.extend(self._append_input_tags())
            if username and not tag_name:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
                search_tags.append(self._build_tag(key='LaunchTime', value=volume.get('CreateTime')))
            else:
                search_tags.extend(self._fill_na_tags())
                search_tags.extend(self._append_input_tags())
                search_tags.append(self._build_tag(key='LaunchTime', value=volume.get('CreateTime')))
            if search_tags:
                if self.dry_run == 'no':
                    self.ec2_client.delete_tags(Resources=[volume_id], Tags=search_tags)
                    logger.info(f'Remove tags of volume_id: {volume_id} total: {len(search_tags)}  tags: {search_tags}')
                volume_ids.append(volume_id)
        logger.info(f'non_cluster_volumes count: {len(sorted(volume_ids))} {sorted(volume_ids)}')
        return sorted(volume_ids)

    def update_snapshots(self, snapshots: list = None):
        """
        This method removes the tags of  non-cluster snapshots
        @param snapshots:
        @return:
        """
        if not snapshots:
            snapshots = self._get_resource_data(resource_method=self.ec2_operations.get_snapshots)
        snapshot_ids = []
        for snapshot in snapshots:
            snapshot_id = snapshot.get('SnapshotId')
            username = self._get_username_from_cloudtrail(start_time=snapshot.get('StartTime'), resource_id=snapshot_id, resource_type='AWS::EC2::Snapshot')
            search_tags = []
            if not username:
                if snapshot.get('Description') and 'Created' in snapshot.get('Description'):
                    image_tags, username = self._get_tags_from_snapshot_description_images(description=snapshot.get('Description'))
                    if not username:
                        instance_id = snapshot.get('Description').split(" ")[2].split("(")[1][:-1]
                        instances = self._get_instances_data(instance_id)
                        if instances:
                            for item in instances:
                                if item.get('InstanceId') == instance_id:
                                    item_tags, username = self._get_tags_from_instance_item(instance_item=item)
            else:
                search_tags.extend(self._append_input_tags())
            if username:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
            else:
                search_tags.extend(self._fill_na_tags())
                search_tags.extend(self._append_input_tags())
            search_tags.append(self._build_tag(key='LaunchTime', value=snapshot.get('StartTime')))
            if search_tags:
                if self.dry_run == 'no':
                    self.ec2_client.delete_tags(Resources=[snapshot_id], Tags=search_tags)
                    logger.info(
                        f'Remove tags of snapshots: {snapshot_id} total: {len(search_tags)} tags: {search_tags}')
                snapshot_ids.append(snapshot_id)
        logger.info(f'non_cluster_snapshot count: {len(sorted(snapshot_ids))} {sorted(snapshot_ids)}')
        return sorted(snapshot_ids)

    def update_ami(self, images: list = None):
        """
        This method removes the tags of non-cluster Amazon Machine Images
        @param images:
        @return:
        """
        if not images:
            images = self.ec2_operations.get_images()
            _, images = self.ec2_operations.scan_cluster_non_cluster_resources(images)
        image_ids = []
        for image in images:
            image_id = image.get('ImageId')
            start_time = datetime.fromisoformat(image.get('CreationDate')[:-1] + '+00:00')
            username = self._get_username_from_cloudtrail(start_time=start_time, resource_id=image_id, resource_type='AWS::EC2::Ami')
            search_tags = []
            search_tags.extend(self._append_input_tags())
            if username:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
            else:
                search_tags.extend(self._fill_na_tags())
            search_tags.append(self._build_tag(key='LaunchTime', value=start_time))
            if search_tags:
                if self.dry_run == 'no':
                    self.ec2_client.delete_tags(Resources=[image_id], Tags=search_tags)
                    logger.info(f'Remove tags of image: {image_id} total: {len(search_tags)} tags: {search_tags}')
                image_ids.append(image_id)
        logger.info(f'non_cluster_amis count: {len(sorted(image_ids))} {sorted(image_ids)}')
        return sorted(image_ids)
