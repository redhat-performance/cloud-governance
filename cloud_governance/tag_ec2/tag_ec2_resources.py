from datetime import timedelta, datetime, timezone

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.iam.iam_operations import IAMOperatons
from cloud_governance.common.logger.init_logger import logger


class TagEc2Resources:
    """
    This class update tags
    """

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes', input_tags: dict = ''):
        self.region = region
        self.dry_run = dry_run
        self.input_tags = input_tags
        self.cloudtrail = boto3.client('cloudtrail', region_name=region)
        self.cluster_prefix = 'kubernetes.io/cluster/'
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cloudtrail = CloudTrailOperations(region_name=self.region)
        self.iam_client = IAMOperatons()

    def __get_instances_data(self, instance_id: str = ''):
        """
        This method go over all instances
        :return:
        """
        instances_list = []
        if instance_id:
            ec2s = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        else:
            ec2s = self.ec2_client.describe_instances()
        ec2s_data = ec2s['Reservations']
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

    def __get_instance_user_tags(self, instance):
        add_tags = []
        instance_id = ''
        for item in instance:
            instance_id = item.get('InstanceId')
            launch_time = item.get('LaunchTime')
            username = self.cloudtrail.get_username(launch_time, instance_id, 'AWS::EC2::Instance')
            user_tags = self.iam_client.get_user_tags(username=username)
            tag_name = username + '-' + instance_id[-4:]
            search_tags = [{'Key': 'Name', 'Value': tag_name}]
            search_tags.extend(self.__append_input_tags())
            search_tags.extend(user_tags)
            add_tags = self.__get_tags_of_resources(tags=item.get('Tags'), search_tags=search_tags)
        return [add_tags, instance_id]

    def update_ec2(self):
        instances_list = self.__get_instances_data()
        instances_ids = []
        for instance in instances_list:
            cluster = False
            for item in instance:
                if item.get('Tags'):
                    for tag in item.get('Tags'):
                        if tag.get('Key').startswith(f'{self.cluster_prefix}'):
                            cluster = True
                            break
            if not cluster:
                add_tags, instance_id = self.__get_instance_user_tags(instance=instance)
                logger.info(add_tags)
                if add_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.create_tags(Resources=[instance_id], Tags=add_tags)
                        logger.info(f'added tags to instance: {instance_id} by tags: {add_tags}')
                    instances_ids.append(instance_id)
        return instances_ids

    def update_volumes(self):
        volumes_data = self.ec2_client.describe_volumes()['Volumes']
        volume_ids = []
        for volume in volumes_data:
            cluster = False
            volume_id = volume.get('VolumeId')
            if volume.get('Tags'):
                for tag in volume.get('Tags'):
                    if tag.get('Key').startswith(f'{self.cluster_prefix}'):
                        cluster = True
                        break
            if not cluster:
                username = self.cloudtrail.get_username(volume.get('CreateTime'), volume_id, 'AWS::EC2::Volume')
                search_tags = []
                if not username:
                    for attachment in volume.get('Attachments'):
                        for instance in self.__get_instances_data(attachment.get('InstanceId')):
                            for item in instance:
                                if item.get('tags'):
                                    search_tags.extend([tag for tag in item.get('Tags') if not tag.get('Key') == 'Name'])
                                else:
                                    search_tags.extend(self.__append_input_tags())
                                username = self.cloudtrail.get_username(item.get('LaunchTime'), item.get('InstanceId'), 'AWS::EC2::Instance')
                                break
                else:
                    search_tags.extend(self.__append_input_tags())
                user_tags = self.iam_client.get_user_tags(username=username)
                search_tags.extend(user_tags)
                tag_name = username + '-' + volume_id[-4:]
                search_tags.append({'Key': 'Name', 'Value': tag_name})
                volume_tags = self.__get_tags_of_resources(tags=volume.get('Tags'), search_tags=search_tags)
                logger.info(volume_tags)
                if volume_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.create_tags(Resources=[volume_id], Tags=volume_tags)
                        logger.info(f'added tags to volume: {volume_id} by tags: {volume_tags}')
                    volume_ids.append(volume_id)
        return volume_ids

    def update_snapshots(self):
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
        snapshot_ids = []
        for snapshot in snapshots:
            cluster = False
            if snapshot.get('Tags'):
                for tag in snapshot.get('Tags'):
                    if tag.get('Key').startswith(f'{self.cluster_prefix}'):
                        cluster = True
            if not cluster:
                snapshot_id = snapshot.get('SnapshotId')
                username = self.cloudtrail.get_username(snapshot.get('StartTime'), snapshot_id, 'AWS::EC2::Snapshot')
                search_tags = []
                if not username:
                    if snapshot.get('Description'):
                        image_id = snapshot.get('Description').split(" ")[-1]
                        images = self.ec2_client.describe_images(Owners=['self'])['Images']
                        for image in images:
                            if image.get('ImageId') == image_id:
                                if image.get('tags'):
                                    search_tags.extend([tag for tag in image.get('Tags') if not tag.get('Key') == "Name"])
                                else:
                                    search_tags.extend(self.__append_input_tags())
                                start_time = datetime.fromisoformat(image.get('CreationDate')[:-1] + '+00:00')
                                username = self.cloudtrail.get_username(start_time=start_time, resource_id=image_id, resource_type='AWS::EC2::Ami')
                                break
                        if not username:
                            instance_id = snapshot.get('Description').split(" ")[2].split("(")[1][:-1]
                            for instance in self.__get_instances_data(instance_id):
                                for item in instance:
                                    if item.get('tags'):
                                        search_tags.extend(
                                            [tag for tag in item.get('Tags') if not tag.get('Key') == 'Name'])
                                    else:
                                        search_tags.extend(self.__append_input_tags())
                                    username = self.cloudtrail.get_username(item.get('LaunchTime'),
                                                                            item.get('InstanceId'),
                                                                            'AWS::EC2::Instance')
                                    break

                else:
                    search_tags.extend(self.__append_input_tags())
                if username:
                    user_tags = self.iam_client.get_user_tags(username=username)
                    search_tags.extend(user_tags)
                    tag_name = username + '-' + snapshot_id[-4:]
                    search_tags.append({'Key': 'Name', 'Value': tag_name})
                else:
                    search_tags.append({'Key': 'Name', 'Value': f'{snapshot_id[:4]}-{self.region}-{snapshot_id[-4:]}'})
                snapshot_tags = self.__get_tags_of_resources(tags=snapshot.get('Tags'), search_tags=search_tags)
                logger.info(snapshot_tags)
                if snapshot_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.create_tags(Resources=[snapshot_id], Tags=snapshot_tags)
                        logger.info(f'added tags to snapshots: {snapshot_id} by tags: {snapshot_tags}')
                    snapshot_ids.append(snapshot_id)
        return snapshot_ids

    def update_ami(self):
        images = self.ec2_client.describe_images(Owners=['self'])['Images']
        image_ids = []
        for image in images:
            cluster = False
            if image.get('Tags'):
                for tag in image.get('Tags'):
                    if tag.get('Key').startswith(f'{self.cluster_prefix}'):
                        cluster = True
            if not cluster:
                image_id = image.get('ImageId')
                start_time = datetime.fromisoformat(image.get('CreationDate')[:-1]+'+00:00')
                username = self.cloudtrail.get_username(start_time=start_time, resource_id=image_id, resource_type='AWS::EC2::Ami')
                user_tags = self.iam_client.get_user_tags(username=username)
                tag_name = username + '-' + image_id[-4:]
                search_tags = [{'Key': 'Name', 'Value': tag_name}]
                search_tags.extend(self.__append_input_tags())
                search_tags.extend(user_tags)
                image_tags = self.__get_tags_of_resources(tags=image.get('Tags'), search_tags=search_tags)
                logger.info(image_tags)
                if image_tags:
                    if self.dry_run == 'no':
                        self.ec2_client.create_tags(Resources=[image_id], Tags=image_tags)
                        logger.info(f'added tags to image: {image_id} by tags: {image_tags}')
                    image_ids.append(image_id)
        return image_ids

