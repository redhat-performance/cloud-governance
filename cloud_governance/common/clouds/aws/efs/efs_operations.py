from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client


class EFSOperations:
    """
    This class contains methods for elastic file system operations
    """

    def __init__(self, region_name: str):
        self._client = get_boto3_client('efs', region_name=region_name)
        self.cluster_prefix = 'kubernetes.io/cluster'

    def describe_efs(self):
        """
        This method returns the efs
        :return:
        """
        try:
            return self._client.describe_file_systems().get('FileSystems', [])
        except Exception as e:
            return []

    def get_cluster_efs(self):
        """
        This method returns the cluster efs
        :return:
        """
        file_systems = self.describe_efs()
        cluster_file_systems = []
        for file_system in file_systems:
            tags = file_system.get('Tags', [])
            for tag in tags:
                if tag['Key'].startswith(self.cluster_prefix):
                    cluster_file_systems.append(file_system)
                    break
        return cluster_file_systems

    def describe_mount_targets(self, resource_id: str):
        """
        This method returns the mount targets
        :param resource_id:
        :return:
        """
        return self._client.describe_mount_targets(FileSystemId=resource_id).get('MountTargets', [])

    def delete_mount_target(self, mount_targets: list):
        """
        This method deletes the mount target
        :param mount_targets:
        :return:
        """
        try:
            [self._client.delete_file_system(FileSystemId=efs_mount.get('MountTargetId')) for efs_mount in
             mount_targets]
            return True
        except Exception as err:
            raise err

    def delete_efs_mount_targets(self, efs_ids: list):
        """
        Delete Mount targets before deleting the EFS file system
        :param efs_ids:
        :return:
        """
        for resource_id in efs_ids:
            try:
                efs_mount_data = self.describe_mount_targets(resource_id)
                self.delete_mount_target(efs_mount_data)
            except Exception as err:
                raise err

    def delete_efs_filesystem(self, resource_ids: list) -> bool:
        """
        This method deletes the efs file system
        :param resource_ids:
        :return:
        """
        self.delete_efs_mount_targets(resource_ids)
        try:
            [self._client.delete_file_system(FileSystemId=resource_id) for resource_id in resource_ids]
            return True
        except Exception as err:
            raise err
