import datetime

from cloud_governance.common.helpers.aws.aws_policy_operations import AWSPolicyOperations
from cloud_governance.policy.abstract_policies.cleanup.abstractinstance_run import AbstractInstanceRun


class InstanceRun(AbstractInstanceRun, AWSPolicyOperations):

    def __init__(self):
        super().__init__()

    def _update_instance_type_count(self):
        """
        This method returns the instance types count by region
        :return: { region: { instance_type: count } }
        :rtype: dict
        """
        instance_types = {}
        resources = self._get_al_instances()
        for instance in resources:
            instance_type = instance.get('InstanceType')
            instance_types.setdefault(self._region, {}).update(
                {instance_type: instance_types.get(instance_type, 0) + 1}
            )
        return instance_types

    def _instance_run(self):
        """
        This method returns the running instances
        :return:
        :rtype:
        """
        instances = self._get_al_instances()
        running_instances_data = []
        for instance in instances:
            tags = instance.get('Tags', [])
            if instance.get('State', {}).get('Name') == 'running':
                running_days = self.calculate_days(instance.get('LaunchTime'))
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(
                    resource_id=instance.get('InstanceId'), tags=tags,
                    clean_up_days=cleanup_days)
                resource_data = self._get_es_data_schema_format(
                    resource_id=instance.get('InstanceId'),
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    instance_type=instance.get('InstanceType'),
                    instance_state=instance.get('State', {}).get('Name') if not cleanup_result else 'stopped',
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                    region=self._region, cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name
                )
                if self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_instances_data.append(resource_data)
            else:
                cleanup_days = 0
            self.update_resource_day_count_tag(resource_id=instance.get('InstanceId'), cleanup_days=cleanup_days,
                                               tags=tags)

        return running_instances_data
