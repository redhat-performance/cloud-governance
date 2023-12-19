import datetime

from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import \
    NonClusterZombiePolicy


class EC2Run(NonClusterZombiePolicy):

    RESOURCE_ACTION = "Stopped"

    def __init__(self):
        super(EC2Run, self).__init__()
        self.__es_index = 'cloud-governance-ec2-instance-types'

    def __update_instance_type_count(self, instances: list):
        """
        This method updates the instance types count
        :param instances:
        :type instances:
        :return:
        :rtype:
        """
        instance_types = {}
        for instance in instances:
            instance_type = instance.get('InstanceType')
            instance_types[instance_type] = instance_types.get(instance_type, 0) + 1
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

    def __ec2_run(self):
        """
        This method list the running instances and upload to elastic_search
        :return:
        :rtype:
        """
        instances = self._ec2_operations.get_ec2_instance_list()
        self.__update_instance_type_count(instances=instances)
        running_instances_data = []
        for instance in instances:
            tags = instance.get('Tags', [])
            if instance.get('State', {}).get('Name') == 'running':
                running_days = self._calculate_days(instance.get('LaunchTime'))
                cleanup_days = self._aws_cleanup_policies.get_clean_up_days_count(tags=tags)
                cleanup_result = self._aws_cleanup_policies.verify_and_delete_resource(
                    resource_id=instance.get('InstanceId'), tags=tags,
                    clean_up_days=cleanup_days)
                resource_data = {
                        'ResourceId': instance.get('InstanceId'),
                        'User': self._get_tag_name_from_tags(tags=tags, tag_name='User'),
                        'SkipPolicy': self._aws_cleanup_policies.get_skip_policy_value(tags=tags),
                        'LaunchTime': instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        'InstanceType': instance.get('InstanceType'),
                        'InstanceState': instance.get('State', {}).get('Name') if not cleanup_result else 'stopped',
                        'StateTransitionReason': instance.get('StateTransitionReason'),
                        'RunningDays': running_days,
                        'CleanUpDays': cleanup_days,
                        'DryRun': self._dry_run,
                        'Name': self._get_tag_name_from_tags(tags=tags, tag_name='Name'),
                        'RegionName': self._region,
                        f'Resource{self.RESOURCE_ACTION}': str(cleanup_result)
                }
                if self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_instances_data.append(resource_data)
            else:
                cleanup_days = 0
            self._aws_cleanup_policies.update_resource_day_count_tag(resource_id=instance.get('InstanceId'),
                                                                     cleanup_days=cleanup_days, tags=tags)

        return running_instances_data

    def run(self):
        """
        This method list all the running instances
        @return:
        """
        return self.__ec2_run()
