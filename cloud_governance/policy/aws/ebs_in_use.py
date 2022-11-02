import json

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EbsInUse(NonClusterZombiePolicy):

    def __init__(self):
        super(EbsInUse, self).__init__()

    def run(self):
        """
        This method list all in-use ebs volumes
        @return:
        """
        in_use_volumes = []
        volumes = self._ec2_operations.get_volumes()
        for volume in volumes:
            if volume.get('State') == 'in-use':
                in_use_volumes.append(volume)
        return self._organise_instance_data(in_use_volumes)
