import json

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EC2Run(NonClusterZombiePolicy):

    def __init__(self):
        super(EC2Run, self).__init__()

    def run(self):
        """
        This method list all in-use ebs volumes
        @return:
        """
        running_instances = []
        instances = self._ec2_operations.get_instances()
        for instance in instances:
            for resource in instance['Instances']:
                if resource.get('State').get('Name') == 'running':
                    running_instances.append(resource)
        return self._organise_instance_data(running_instances)
