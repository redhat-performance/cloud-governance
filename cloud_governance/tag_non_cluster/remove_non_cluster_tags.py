from datetime import datetime

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class RemoveNonClusterTags:

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes', input_tags: dict = ''):
        self.region = region
        self.dry_run = dry_run
        self.input_tags = input_tags
        self.cloudtrail = boto3.client('cloudtrail', region_name=region)
        self.cluster_prefix = 'kubernetes.io/cluster/'
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cloudtrail = CloudTrailOperations(region_name=self.region)
        self.iam_client = IAMOperations()
        self.ec2_operations = EC2Operations(region=region)
        self.utils = Utils(region=region)

    def __get_instances_data(self, instance_id: str = ''):
        """
        This method go over all instances
        :return:
        """
        ec2s_data = self.ec2_operations.get_instances()
        if instance_id:
            for items in ec2s_data:
                if items.get('Instances'):
                    for item in items['Instances']:
                        if item.get('InstanceId') == instance_id:
                            return items['Instances']
        else:
            instances_list = []
            for items in ec2s_data:
                if items.get('Instances'):
                    instances_list.append(items['Instances'])
            return instances_list

    def __append_input_tags(self):
        """
        This method build tags list according to input tags dictionary
        @return:
        """
        tags_list = []
        for key, value in self.input_tags.items():
            tags_list.append({'Key': key, 'Value': value})
        return tags_list

    def __get_tags_of_resources(self, tags: list, search_tags: list):
        """
        This method extracts tags from the resource tags
        @param tags:
        @param search_tags:
        @return:
        """
        add_tags = []
        if tags:
            for search_tag in search_tags:
                found = False
                for tag in tags:
                    if tag.get('Key') == search_tag.get('Key'):
                        found = True
                if not found:
                    add_tags.append(search_tag)
        else:
            add_tags.extend(search_tags)
        return add_tags

    def __get_instance_tags(self, launch_time: datetime, instance_id: str, tags: list):
        """
        This method returns the tags to update  the instance tags
        @param launch_time:
        @param instance_id:
        @param tags:
        @return:
        """
        username = self.cloudtrail.get_username_by_instance_id_and_time(launch_time, instance_id, 'AWS::EC2::Instance')
        search_tags = []
        user_tags = self.iam_client.get_user_tags(username=username)
        if not username:
            search_tags.append({'Key': 'User', 'Value': 'NA'})
            search_tags.append({'Key': 'Manager', 'Value': 'NA'})
            search_tags.append({'Key': 'Project', 'Value': 'NA'})
            search_tags.append({'Key': 'Email', 'Value': 'NA'})
            search_tags.append({'Key': 'Environment', 'Value': 'NA'})
            search_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
        else:
            search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
        search_tags.extend([{'Key': 'LaunchTime', 'Value': launch_time.strftime('%Y/%m/%d %H:%M:%S')}])
        search_tags.extend(self.__append_input_tags())
        search_tags.extend(user_tags)
        return search_tags

    def non_cluster_update_ec2(self, instances_list: list = None):
        """
        This method removes the tags of ec2 instances
        @return:
        """
        if not instances_list:
            instances_list = self.__get_instances_data()
            _, instances_list = self.ec2_operations.scan_cluster_or_non_cluster_instance(instances_list)
        instances_ids = []
        for instance in instances_list:
            for item in instance:
                instance_id = item.get('InstanceId')
                launch_time = item.get('LaunchTime')
                add_tags = self.__get_instance_tags(launch_time=launch_time, instance_id=instance_id,
                                                    tags=item.get('Tags'))
                if add_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.delete_tags(Resources=[instance_id], Tags=add_tags)
                        logger.info(f'delete tags of instance: {instance_id} total: {len(add_tags)} tags: {add_tags}')
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
            volumes_data = self.ec2_operations.get_volumes()
            _, volumes_data = self.ec2_operations.scan_cluster_non_cluster_resources(volumes_data)
        volume_ids = []
        for volume in volumes_data:
            volume_id = volume.get('VolumeId')
            tag_name = ''
            username = self.cloudtrail.get_username_by_instance_id_and_time(volume.get('CreateTime'), volume_id,
                                                                            'AWS::EC2::Volume')
            search_tags = []
            if not username:
                if volume.get('Attachments'):
                    for attachment in volume.get('Attachments'):
                        for item in self.__get_instances_data(attachment.get('InstanceId')):
                            if item.get('tags'):
                                search_tags.extend(
                                    [tag for tag in item.get('Tags') if not tag.get('Key') == 'Name'])
                                for tag in item.get('Tags'):
                                    if tag.get('Key') == 'User':
                                        username = tag.get('Key')
                                    elif tag.get('Key') == 'LaunchTime':
                                        search_tags.append({'Key': 'LaunchTime', 'Value': tag.get('Key')})
                            else:
                                search_tags.extend(self.__append_input_tags())
                                username = self.cloudtrail.get_username_by_instance_id_and_time(
                                    item.get('LaunchTime'), item.get('InstanceId'), 'AWS::EC2::Instance')
                                search_tags.append({'Key': 'LaunchTime',
                                                    'Value': item.get('LaunchTime').strftime('%Y/%m/%d %H:%M:%S')})
                            break
                else:
                    search_tags.extend(self.__append_input_tags())
            else:
                search_tags.extend(self.__append_input_tags())
            if username and not tag_name:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
                search_tags.append(
                    {'Key': 'LaunchTime', 'Value': volume.get('CreateTime').strftime('%Y/%m/%d %H:%M:%S')})
            else:
                search_tags.append({'Key': 'User', 'Value': 'NA'})
                search_tags.append({'Key': 'Manager', 'Value': 'NA'})
                search_tags.append({'Key': 'Project', 'Value': 'NA'})
                search_tags.append({'Key': 'Email', 'Value': 'NA'})
                search_tags.append({'Key': 'Environment', 'Value': 'NA'})
                search_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
                search_tags.extend(self.__append_input_tags())
                search_tags.append(
                    {'Key': 'LaunchTime', 'Value': volume.get('CreateTime').strftime('%Y/%m/%d %H:%M:%S')})
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
            snapshots = self.ec2_operations.get_snapshots()
            _, snapshots = self.ec2_operations.scan_cluster_non_cluster_resources(snapshots)
        snapshot_ids = []
        for snapshot in snapshots:
            snapshot_id = snapshot.get('SnapshotId')
            username = self.cloudtrail.get_username_by_instance_id_and_time(snapshot.get('StartTime'), snapshot_id,
                                                                            'AWS::EC2::Snapshot')
            search_tags = []
            if not username:
                if snapshot.get('Description') and 'Created' in snapshot.get('Description'):
                    image_id = snapshot.get('Description').split(" ")[-1]
                    images = self.ec2_client.describe_images(Owners=['self'])['Images']
                    for image in images:
                        if image.get('ImageId') == image_id:
                            if image.get('tags'):
                                search_tags.extend(
                                    [tag for tag in image.get('Tags') if not tag.get('Key') == "Name"])
                            else:
                                search_tags.extend(self.__append_input_tags())
                            start_time = datetime.fromisoformat(image.get('CreationDate')[:-1] + '+00:00')
                            username = self.cloudtrail.get_username_by_instance_id_and_time(start_time=start_time,
                                                                                            resource_id=image_id,
                                                                                            resource_type='AWS::EC2::Ami')
                            break
                    if not username:
                        instance_id = snapshot.get('Description').split(" ")[2].split("(")[1][:-1]
                        instances = self.__get_instances_data(instance_id)
                        if instances:
                            for item in instances:
                                if item.get('InstanceId') == instance_id:
                                    if item.get('Tags'):
                                        search_tags.extend(
                                            [tag for tag in item.get('Tags') if not tag.get('Key') == 'Name'])
                                    else:
                                        search_tags.extend(self.__append_input_tags())
                                    username = self.cloudtrail.get_username_by_instance_id_and_time(
                                        item.get('LaunchTime'),
                                        item.get('InstanceId'),
                                        'AWS::EC2::Instance')
                                    search_tags.append({'Key': 'LaunchTime', 'Value': item.get('LaunchTime').strftime('%Y/%m/%d %H:%M:%S')})
                                    break
            else:
                search_tags.extend(self.__append_input_tags())
            if username:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
                search_tags.append(
                    {'Key': 'LaunchTime', 'Value': snapshot.get('StartTime').strftime('%Y/%m/%d %H:%M:%S')})
            else:
                search_tags.append({'Key': 'User', 'Value': 'NA'})
                search_tags.append({'Key': 'Manager', 'Value': 'NA'})
                search_tags.append({'Key': 'Project', 'Value': 'NA'})
                search_tags.append({'Key': 'Email', 'Value': 'NA'})
                search_tags.append({'Key': 'Environment', 'Value': 'NA'})
                search_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
                search_tags.extend(self.__append_input_tags())
                search_tags.append(
                    {'Key': 'LaunchTime', 'Value': snapshot.get('StartTime').strftime('%Y/%m/%d %H:%M:%S')})
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
            username = self.cloudtrail.get_username_by_instance_id_and_time(start_time=start_time,
                                                                            resource_id=image_id,
                                                                            resource_type='AWS::EC2::Ami')
            search_tags = []
            search_tags.extend(self.__append_input_tags())
            if username:
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                search_tags.append({'Key': 'Email', 'Value': f'{username}@redhat.com'})
            else:
                search_tags.append({'Key': 'User', 'Value': 'NA'})
                search_tags.append({'Key': 'Manager', 'Value': 'NA'})
                search_tags.append({'Key': 'Project', 'Value': 'NA'})
                search_tags.append({'Key': 'Email', 'Value': 'NA'})
                search_tags.append({'Key': 'Environment', 'Value': 'NA'})
                search_tags.append(({'Key': 'Owner', 'Value': 'NA'}))
            search_tags.extend([{'Key': 'LaunchTime', 'Value': start_time.strftime('%Y/%m/%d %H:%M:%S')}])
            if search_tags:
                if self.dry_run == 'no':
                    self.ec2_client.delete_tags(Resources=[image_id], Tags=search_tags)
                    logger.info(f'Remove tags of image: {image_id} total: {len(search_tags)} tags: {search_tags}')
                image_ids.append(image_id)
        logger.info(f'non_cluster_amis count: {len(sorted(image_ids))} {sorted(image_ids)}')
        return sorted(image_ids)
