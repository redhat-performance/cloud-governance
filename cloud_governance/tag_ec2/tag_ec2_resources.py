import json
from datetime import timedelta, datetime, timezone

import boto3
import requests

from cloud_governance.common.logger.init_logger import logger


class TagEc2Resources:
    """
    This class update tags
    """

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes'):
        self.region = region
        self.dry_run = dry_run
        self.cloudtrail = boto3.client('cloudtrail')
        self.ec2_client = boto3.client('ec2', region_name=region)
        # self.update_tags_api_url = f'https://47ppxz9hie.execute-api.us-east-2.amazonaws.com/v1/update?region={self.region}'

    # @todo write separate class
    def __get_user_from_trail_events(self, date_time):
        """
        This method find user name in cloud trail events according to date time
        @param date_time:
        @return:
        """
        diff = timedelta(seconds=1)
        end_date_time = date_time + diff
        try:
            response = self.cloudtrail.lookup_events(
                StartTime=date_time,
                EndTime=end_date_time,
                MaxResults=123
            )
        except:
            return ''
        if response:
            for event in response['Events']:
                if event.get('Username'):
                    return event['Username']

    def update_volumes(self):
        """
        This method creates a tags for volumes
        first search in  cloudtrail if notfound search in instances
        @return:
        """
        volumes = self.ec2_client.describe_volumes()['Volumes']
        volume_ids = []
        for volume in volumes:
            volume_id = volume.get('VolumeId')
            if not volume.get('Tags'):
                if self.dry_run == 'no':
                    username = self.__get_user_from_trail_events(date_time=volume.get('CreateTime'))
                    if not username:
                        for attachments in volume.get('Attachments'):
                            instances = self.ec2_client.describe_instances(InstanceIds=[attachments.get('InstanceId')])['Reservations'][0]
                            for instance in instances['Instances']:
                                for tag in instance.get('Tags'):
                                    if tag.get('Key') == 'Username':
                                        username = tag.get("Value")
                                        break
                    tags = [{
                        'Key': 'Username',
                        'Value': username
                    },
                        {
                            'Key': 'CreateTime',
                            'Value': str(volume.get('CreateTime'))
                        }]
                    self.ec2_client.create_tags(Resources=[volume_id], Tags=tags)
                    logger.info(f'updated tags of instance id: {volume_id} by tags : {tags}')
                volume_ids.append(volume_id)
        return volume_ids

    def update_ami(self):
        """
        This method creates a tags for AMI
        @return:
        """
        images = self.ec2_client.describe_images(Owners=['self'])['Images']
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
        images_ids = []
        for image in images:
            image_id = image.get('ImageId')
            if not image.get('Tags'):
                if self.dry_run == 'no':
                    username = ''
                    for snapshot in snapshots:
                        for mapping in image.get('BlockDeviceMappings'):
                            if mapping.get('Ebs').get('SnapshotId') == snapshot.get('SnapshotId'):
                                snap_tags = snapshot.get('Tags')
                                for tag in snap_tags:
                                    if tag.get('Key') == "Username":
                                        username = tag.get('Value')
                                        break
                                break
                    tags = [{
                        'Key': 'Username',
                        'Value': username
                    }, {
                        'Key': 'CreateTime',
                        'Value': str(image.get('CreationDate'))
                    }
                    ]
                    self.ec2_client.create_tags(Resources=[image_id], Tags=tags)
                    logger.info(f'updated tags of ami: {image_id} by tags : {tags}')
                images_ids.append(image_id)
        return images_ids

    def update_snapshots(self):
        """
        This method create tags for snapshots
        search in a cloud trail if not found search in volumes
        @return:
        """
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
        volumes = self.ec2_client.describe_volumes()['Volumes']
        snapshot_ids = []
        for snapshot in snapshots:
            snapshot_id = snapshot.get('SnapshotId')
            if not snapshot.get('Tags'):
                if self.dry_run == 'no':
                    username = self.__get_user_from_trail_events(snapshot.get('StartTime'))
                    if not username:
                        for volume in volumes:
                            if volume.get('VolumeId') == snapshot.get('VolumeId'):
                                vol_tags = volume.get('Tags')
                                for tag in vol_tags:
                                    if tag.get('Key') == 'Username':
                                        username = tag.get('Value')
                                        break
                    tags = [{
                        'Key': 'Username',
                        'Value': username
                    }, {
                        'Key': 'CreateTime',
                        'Value': str(snapshot.get('StartTime'))
                    }
                    ]
                    self.ec2_client.create_tags(Resources=[snapshot_id], Tags=tags)
                    logger.info(f'updated tags of snapshots: {snapshot_id} by tags : {tags}')
                snapshot_ids.append(snapshot_id)
        return snapshot_ids

    def update_ec2(self):
        """
        This method update ec2 tags
        """
        ec2_instances = self.ec2_client.describe_instances()['Reservations']
        instances_ids = {}
        for resource in ec2_instances:
            if resource.get('Instances'):
                for instance in resource.get('Instances'):
                    if not instance.get('Tags'):
                        instances_ids[instance.get('InstanceId')] = instance.get('LaunchTime')
        if self.dry_run == 'no':
            for instance_id, date_time in instances_ids.items():
                username = self.__get_user_from_trail_events(date_time=date_time)
                tags = [{
                    'Key': 'Username',
                    'Value': username
                },
                    {
                        'Key': 'CreateTime',
                        'Value': str(date_time)
                    }]
                self.ec2_client.create_tags(Resources=[instance_id], Tags=tags)
                logger.info(f'updated tags of instance id: {instance_id} by tags : {tags}')
        return list(instances_ids.keys())

