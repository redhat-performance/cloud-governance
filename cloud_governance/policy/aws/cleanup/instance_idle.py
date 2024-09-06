from cloud_governance.common.utils.configs import INSTANCE_IDLE_DAYS
from cloud_governance.common.utils.utils import Utils
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class InstanceIdle(AWSPolicyOperations):
    """
    This class stop the idle ec2 instances more than 4 days if the matches the required metrics
    CpuUtilization < 2 percent
    NetworkIN < 5k bytes
    NetworkOut < 5k bytes
    We trigger email if the ec2 instance is idle 2 days and stop the instance if it is idle 4 days
    """
    RESOURCE_ACTION = 'Stop'

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the running instances
        :return:
        :rtype:
        """
        instances = self._get_all_instances()
        idle_instances = []
        for instance in instances:
            instance_id = instance.get('InstanceId')
            status = instance.get('State', {}).get('Name')
            tags = instance.get('Tags', [])
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_result = False
            running_days = self.calculate_days(instance.get('LaunchTime'))
            if Utils.contains_ignore_case(string=status, str1='running') and \
                    not cluster_tag and \
                    Utils.greater_than(val1=running_days, val2=INSTANCE_IDLE_DAYS) and \
                    self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP') and \
                    self.verify_instance_idle(resource_id=instance_id):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                unit_price = self._resource_pricing.get_ec2_price(region_name=self._region,
                                                                  instance_type=instance.get('InstanceType'),
                                                                  operating_system=instance.get('PlatformDetails'))
                cleanup_result = self.verify_and_delete_resource(resource_id=instance_id, tags=tags,
                                                                 clean_up_days=cleanup_days)
                resource_data = self._get_es_schema(
                    resource_id=instance_id,
                    skip_policy=self.get_skip_policy_value(tags=tags),
                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                    launch_time=instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    resource_type=instance.get('InstanceType'),
                    resource_state=status if not cleanup_result else self.RESOURCE_ACTION,
                    running_days=running_days, cleanup_days=cleanup_days,
                    dry_run=self._dry_run,
                    name=self.get_tag_name_from_tags(tags=tags, tag_name='Name'),
                    resource_action=self.RESOURCE_ACTION,
                    region=self._region, cleanup_result=str(cleanup_result),
                    cloud_name=self._cloud_name,
                    unit_price=unit_price
                )
                if self._force_delete and self._dry_run == 'no':
                    resource_data.update({'ForceDeleted': str(self._force_delete)})
                idle_instances.append(resource_data)
            else:
                cleanup_days = 0
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=instance_id, cleanup_days=cleanup_days, tags=tags)
        return idle_instances
