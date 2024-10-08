from abc import ABC

from cloud_governance.policy.helpers.aws.policy.zombie_cluster_operations import ZombieClusterOperations


class ZombieClusterResource(ZombieClusterOperations, ABC):

    def __init__(self):
        super().__init__()
        self.zombie_cluster_resource_name = self._environment_variables_dict.get('ZOMBIE_CLUSTER_RESOURCE_NAME')

    def get_zombie_cluster_resources(self, resource_list: list, resource_key_id: str,
                                     zombie_cluster_id: str, create_date: str, tags_name: str = 'Tags',
                                     resource_type: str = 'ec2_service'):
        """
        This method returns the zombie cluster resources for a given resource type.
        :param create_date:
        :param tags_name:
        :param zombie_cluster_id:
        :param resource_list:
        :param resource_key_id:
        :param resource_type:
        :return:
        """
        cluster_resources = self._get_cluster_resources(resources_list=resource_list,
                                                        zombie_cluster_id=zombie_cluster_id, tags_name=tags_name)
        zombie_cluster_resources = self.get_zombie_resources(cluster_resources=cluster_resources.copy())
        zombie_cluster_resources = self.process_and_delete_resources(
            zombie_cluster_resources=zombie_cluster_resources.copy(),
            resource_id_key=resource_key_id,
            resource_type=resource_type,
            tags_name=tags_name,
            create_date=create_date)
        return zombie_cluster_resources

    def zombie_cluster_volume(self, zombie_cluster_id: str = None):
        """
        This method returns the list of zombie cluster volumes, and delete them once they reach the delete days
        :param zombie_cluster_id:
        :return:
        """
        volume_id_key = 'VolumeId'
        volume_filters = [{'Name': 'status', 'Values': ['available']}]
        if zombie_cluster_id:
            volume_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])

        available_volumes = self._ec2_operations.get_volumes(Filters=volume_filters)
        return self.get_zombie_cluster_resources(resource_list=available_volumes,
                                                 resource_key_id=volume_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='CreateTime')

    def zombie_cluster_snapshot(self, zombie_cluster_id: str = None):
        """
        This method returns list of zombie cluster's snapshot according to cluster tag name and cluster name data
        :param zombie_cluster_id:
        :return:
        """
        snapshot_id_key = 'SnapshotId'
        snapshot_filters = []
        if zombie_cluster_id:
            snapshot_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        snapshots_data = self._ec2_operations.get_snapshots(Filters=snapshot_filters)
        return self.get_zombie_cluster_resources(resource_list=snapshots_data,
                                                 resource_key_id=snapshot_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='StartTime'
                                                 )

    def zombie_cluster_ami(self, zombie_cluster_id: str = None):
        """
        This method returns list of cluster's ami according to cluster tag name and cluster name data
        """
        image_id_key = 'ImageId'
        image_filters = []
        if zombie_cluster_id:
            image_filters.append([{'Name': f'tag:{zombie_cluster_id}', 'Values': 'owned'}])
        images_data = self._ec2_operations.get_images(Filters=image_filters)
        return self.get_zombie_cluster_resources(resource_list=images_data,
                                                 resource_key_id=image_id_key,
                                                 zombie_cluster_id=zombie_cluster_id,
                                                 create_date='CreationDate')

    def run_zombie_cluster_pruner(self):
        """
        This method run zombie cluster pruner operations
        :return:
        """
        if self.zombie_cluster_resource_name:
            zombie_clusters_resources = [self.zombie_cluster_resource_name]
        else:
            zombie_clusters_resources = [
                self.zombie_cluster_volume,
                self.zombie_cluster_snapshot,
                self.zombie_cluster_ami
            ]
        zombie_cluster_response = {}
        for zombie_cluster in zombie_clusters_resources:
            zombie_items = zombie_cluster()
            for zombie_tag, zombie_resources in zombie_items.items():
                if zombie_tag in zombie_cluster_response:
                    zombie_cluster_response[zombie_tag]['ResourceIds'].extend(zombie_resources['ResourceIds'])
                    resource_names = list(set(zombie_cluster_response[zombie_tag]['ResourceNames']))
                    resource_names.append(zombie_cluster.__name__)
                    zombie_cluster_response[zombie_tag]['ResourceNames'] = list(resource_names)
                else:
                    zombie_cluster_response.setdefault(zombie_tag, {}).update(zombie_resources)
                    zombie_cluster_response[zombie_tag].setdefault('ResourceNames', []).append(zombie_cluster.__name__)
        return zombie_cluster_response

    def run_policy_operations(self):
        return self.run_zombie_cluster_pruner()
