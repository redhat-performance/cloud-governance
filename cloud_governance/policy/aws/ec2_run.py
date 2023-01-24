import datetime

from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EC2Run(NonClusterZombiePolicy):

    def __init__(self):
        super(EC2Run, self).__init__()
        self.__es_index = 'cloud-governance-ec2-instance-types'

    def run(self):
        """
        This method list all in-use ebs volumes
        @return:
        """
        running_instances = []
        instances = self._ec2_operations.get_instances()
        instance_types = {}
        for instance in instances:
            for resource in instance['Instances']:
                if resource.get('State').get('Name') == 'running':
                    running_instances.append(resource)
                instance_type = resource.get('InstanceType')
                instance_types[instance_type] = instance_types.get(instance_type, 0)+1
        es_instance_types_data = []
        for key, value in instance_types.items():
            es_instance_types_data.append({
                'instance_type': key,
                'instance_count': value,
                'timestamp': datetime.datetime.utcnow(),
                'region': self._region,
                'account': self._account.upper().replace('OPENSHIFT-', ''),
                'index_id': f'{key}-{self._account.lower()}-{self._region}-{str(datetime.datetime.utcnow().date())}'
            })
        self._es_upload.es_upload_data(items=es_instance_types_data, es_index=self.__es_index, set_index='index_id')
        return self._organise_instance_data(running_instances)
