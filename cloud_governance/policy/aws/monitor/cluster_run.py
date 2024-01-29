import datetime
import re

from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class ClusterRun(AWSPolicyOperations):
    """
    This class performs the operations on running cluster resources
    """

    def __init__(self):
        super().__init__()

    def run_policy_operations(self):
        """
        This method returns the running vms in the AAzure cloud and stops based on the action
        :return:
        :rtype:
        """
        instances = self._get_all_instances()
        cluster_data = {}
        for instance in instances:
            tags = instance.get('Tags', [])
            cluster_tag = self._get_cluster_tag(tags=tags).strip()
            instance_state = instance.get('State', {}).get('Name')
            if cluster_tag and not string_equal_ignore_case(instance_state, 'terminated'):
                launch_time = instance.get('LaunchTime')
                running_instances = stopped_instances = 0
                running_days = self.calculate_days(instance.get('LaunchTime'))
                if string_equal_ignore_case(instance_state, 'stopped'):
                    stopped_instances = 1
                    state_transition_reason = instance.get('StateTransitionReason')
                    if state_transition_reason:
                        extract_data = re.search(r'\((\d{4}-\d{2}-\d{2})', state_transition_reason)
                        if extract_data:
                            running_days = self.calculate_days(extract_data.group(1).split()[0], start_date=launch_time)
                            instance_state += f"@{extract_data.group(1)}"
                else:
                    running_instances = 1
                instance_data = f"{instance.get('InstanceId')}, {self.get_tag_name_from_tags(tags=tags, tag_name='Name')}, {instance.get('InstanceType')}, {instance_state}, {running_days}, {launch_time}"
                if cluster_tag in cluster_data:
                    cluster_data[cluster_tag]['Instances'].append(instance_data)
                    cluster_data[cluster_tag]['InstanceCount'] = len(cluster_data[cluster_tag]['Instances'])
                    cluster_data[cluster_tag]['Stopped'] = int(cluster_data[cluster_tag]['Stopped']) + stopped_instances
                    cluster_data[cluster_tag]['Running'] = int(cluster_data[cluster_tag]['Running']) + running_instances
                else:
                    cluster_data[cluster_tag] = {
                        'ResourceId': cluster_tag,
                        'ClusterTag': cluster_tag,
                        'User': self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                        'RunningDays': running_days,
                        'RegionName': self._region,
                        'PublicCloud': self._cloud_name,
                        'Instances': [instance_data],
                        'InstanceCount': 1,
                        'Stopped': stopped_instances,
                        'Running': running_instances,
                        'index-id': f'{datetime.datetime.utcnow().date()}-{self._cloud_name.lower()}-{self.account.lower()}-{self._region.lower()}-{cluster_tag}'
                    }
        return list(cluster_data.values())
