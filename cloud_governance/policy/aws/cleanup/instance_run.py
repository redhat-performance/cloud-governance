from datetime import datetime

from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class InstanceRun(AWSPolicyOperations):
    INSTANCE_TYPES_ES_INDEX = "cloud-governance-instance-types"
    RESOURCE_ACTION = "Stopped"

    def __init__(self):
        super().__init__()

    def _upload_instance_type_count_to_elastic_search(self):
        """
        This method uploads the instance type count to elasticsearch
        :return:
        :rtype:
        """
        instance_types = self._update_instance_type_count()
        account = self.account
        current_day = datetime.utcnow()
        es_instance_types_data = []
        for region, instance_types in instance_types.items():
            for instance_type, instance_type_count in instance_types.items():
                es_instance_types_data.append({
                    'instance_type': instance_type,
                    'instance_count': instance_type_count,
                    'timestamp': current_day,
                    'region': region,
                    'account': account,
                    'PublicCloud': self._cloud_name,
                    'index_id': f'{instance_type}-{self._cloud_name.lower()}-{account.lower()}-{region}-{str(current_day.date())}'
                })
        self._es_upload.es_upload_data(items=es_instance_types_data, es_index=self.INSTANCE_TYPES_ES_INDEX,
                                       set_index='index_id')

    def _update_instance_type_count(self):
        """
        This method returns the instance types count by region
        :return: { region: { instance_type: count } }
        :rtype: dict
        """
        instance_types = {}
        resources = self._get_all_instances()
        for instance in resources:
            instance_type = instance.get('InstanceType')
            instance_types.setdefault(self._region, {}).update(
                {instance_type: instance_types.get(self._region).get(instance_type, 0) + 1}
            )
        return instance_types

    def run_policy_operations(self):
        """
        This method returns the running instances
        :return:
        :rtype:
        """
        self._upload_instance_type_count_to_elastic_search()
        instances = self._get_all_instances()
        running_instances_data = []
        for instance in instances:
            tags = instance.get('Tags', [])
            cleanup_result = False

            if instance.get('State', {}).get('Name') == 'running':
                running_days = self.calculate_days(instance.get('LaunchTime'))
                unit_price = self._resource_pricing.get_ec2_price(region_name=self._region,
                                                                  instance_type=instance.get('InstanceType'),
                                                                  operating_system=instance.get('PlatformDetails'))
                if self._shutdown_period:
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(
                        resource_id=instance.get('InstanceId'), tags=tags,
                        clean_up_days=cleanup_days)
                else:
                    cleanup_days = 0
                resource_data = self._get_es_schema(
                    resource_id=instance.get('InstanceId'),
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    resource_type=instance.get('InstanceType'),
                    resource_state=instance.get('State', {}).get('Name') if not cleanup_result else 'stopped',
                    resource_action=self.RESOURCE_ACTION,
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                    region=self._region, cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name,
                    unit_price=unit_price
                )
                if self._shutdown_period and self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                running_instances_data.append(resource_data)
            else:
                cleanup_days = 0
            if self._shutdown_period:
                self.update_resource_day_count_tag(resource_id=instance.get('InstanceId'), cleanup_days=cleanup_days,
                                                   tags=tags)

        return running_instances_data
