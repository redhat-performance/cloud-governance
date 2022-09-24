import csv

import boto3

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.logger.init_logger import logger


class UpdateNATags:

    def __init__(self, file_name: str, region: str = 'us-east-2'):
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.file_name = file_name
        self.ec2_operations = EC2Operations(region=region)

    def __get_resource_data(self, resource: str):
        """
        This method gives resource data
        @return:
        """
        if resource == 'instance':
            instances_data = self.ec2_operations.get_instances()
            instances = []
            for instance in instances_data:
                for resource in instance['Instances']:
                    instances.append(resource)
            return instances
        elif resource == 'volume':
            return self.ec2_operations.get_volumes()
        elif resource == 'snapshot':
            return self.ec2_operations.get_snapshots()
        elif resource == 'image':
            return self.ec2_operations.get_images()

    def __get_resource_ids(self, resource_id: str, resource_name: str):
        """
        This method get all instances
        @return:
        """
        resources = self.__get_resource_data(resource=resource_name)
        resource_ids = []
        for resource in resources:
            resource_ids.append(resource.get(resource_id))
        return resource_ids

    def __get_key_value(self, key, value):
        """
        This method return key-value pairs
        :param key:
        :param value:
        :return:
        """
        return {'Key': key, 'Value': value}

    def __convert_key_value(self, keys, values):
        """
        This return dict of resource and its tags
        :param keys:
        :param values:
        :return: 
        """
        tags = {}
        for value in values:
            tags[value[0]] = []
            for index, tag_value in enumerate(value[1:]):
                if tag_value.strip():
                    tags[value[0]].append(self.__get_key_value(keys[index].strip(), tag_value.strip()))
        return tags

    def __beautify_csv_data_to_key_value_pairs(self):
        """
        This method convert the csv data to key-value pairs
        :return:
        """
        with open(self.file_name) as file:
            csvreader = csv.reader(file)
            header = next(csvreader)[1:]
            rows = []
            for row in csvreader:
                rows.append(row)
            return self.__convert_key_value(header, rows)

    def update_tags(self):
        """
        This method update tags
        @return:
        """
        instances = self.__get_resource_ids(resource_id='InstanceId', resource_name='instance')
        volumes = self.__get_resource_ids(resource_id='VolumeId', resource_name='volume')
        snapshots = self.__get_resource_ids(resource_id='SnapshotId', resource_name='snapshot')
        images = self.__get_resource_ids(resource_id='ImageId', resource_name='image')
        na_resources = self.__beautify_csv_data_to_key_value_pairs()
        co = 0
        for resource, resource_tags in na_resources.items():
            if resource in instances or resource in volumes or resource in snapshots or resource in images:
                co += 1
                self.ec2_client.create_tags(Resources=[resource], Tags=resource_tags)
                logger.info(f'Updated the Tags of {resource}')

        return co

    def __extract_tags(self, tags):
        """
        This method extract tags from the resources
        @param tags:
        @return:
        """
        extract_tags = {}
        tags_list = []
        for tag in tags:
            if not tag.get('Key').startswith('kubernetes.io') and not tag.get('Key').startswith('aws:'):
                extract_tags[tag.get('Key')] = tag.get('Value')
                tags_list.append(tag.get('Key'))
        return [extract_tags, tags_list]

    def __resource_list(self, resource_id: str, resource_name: str):
        """
        This method returns resource_id and tags
        @param resource_id:
        @param resource_name:
        @return:
        """
        resource_ids = {}
        resource_data = self.__get_resource_data(resource=resource_name)
        keys = []
        for resource in resource_data:
            if resource.get('Tags'):
                for tag in resource.get('Tags'):
                    if tag.get("Key") == "User" and tag.get('Value') == 'NA':
                        tags, tag_keys = self.__extract_tags(resource.get('Tags'))
                        resource_ids[resource.get(resource_id)] = tags
                        keys.extend(tag_keys)
                        break
        return [resource_ids, set(keys)]

    def create_csv(self):
        with open(f'{self.file_name}', 'w') as file:
            instances, instance_tags = self.__resource_list(resource_id='InstanceId', resource_name='instance')
            volumes, volume_tags = self.__resource_list(resource_id='VolumeId', resource_name='volume')
            snapshots, snapshot_tags = self.__resource_list(resource_id='SnapshotId', resource_name='snapshot')
            images, images_tags = self.__resource_list(resource_id='ImageId', resource_name='image')
            resources = [instances, volumes, snapshots, images]
            tags = list(set(list(instance_tags) + list(volume_tags) + list(snapshot_tags) + list(images_tags)))
            tags.sort()
            file.write('Resource_Id, ')
            for tag in tags:
                file.write(f'{tag}, ')
            file.write('\n')
            for resource in resources:
                for instance, key_tags in resource.items():
                    file.write(f'{instance}, ')
                    for value in sorted(key_tags):
                        if key_tags.get(value).strip():
                            file.write(f'{key_tags.get(value).strip()}, ')
                        else:
                            file.write(f', ')
                    file.write('\n')
