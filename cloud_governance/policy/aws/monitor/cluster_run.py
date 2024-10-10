import datetime
import re

from math import ceil

from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.common.utils.configs import GRAVITON_MAPPINGS, DEFAULT_ROUND_DIGITS, DEFAULT_GRAVITON_INSTANCE
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class ClusterRun(AWSPolicyOperations):
    """
    This class performs the operations on running cluster resources
    """

    def __init__(self):
        super().__init__()

    def __get_creation_date(self, block_devices: list) -> str:
        """
        This method returns the creation date of the EC2 instance from the root ebs volume.
        :param block_devices:
        :return:
        """
        for devices in block_devices:
            if devices.get('Ebs', {}).get('DeleteOnTermination'):
                return devices.get('Ebs', {}).get('AttachTime').strftime('%Y-%m-%d')
        return ''

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
                name_tag = self.get_tag_name_from_tags(tags=tags, tag_name='Name')
                launch_time = instance.get('LaunchTime')
                running_instances = stopped_instances = 0
                running_days = self.calculate_days(launch_time)
                running_hours = ceil(self.calculate_hours(launch_time))
                stopped_date_time = ''
                if string_equal_ignore_case(instance_state, 'stopped'):
                    stopped_instances = 1
                    state_transition_reason = instance.get('StateTransitionReason')
                    if state_transition_reason:
                        extract_data = re.search(r'\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', state_transition_reason)
                        if extract_data:
                            stopped_date_time = extract_data.group(1)
                            running_days = self.calculate_days(stopped_date_time.split()[0], start_date=launch_time)
                            instance_state += f"@{extract_data.group(1)}"
                else:
                    running_instances = 1
                creation_date = ''
                rosa_cluster = True if self.get_tag_name_from_tags(tags=tags, tag_name='red-hat-managed') else False
                instance_type = instance.get('InstanceType')
                using_graviton = False
                for graviton_instance_family in GRAVITON_MAPPINGS.values():
                    if graviton_instance_family in instance_type:
                        using_graviton = True
                if 'master' in name_tag.lower():
                    creation_date = self.__get_creation_date(instance.get('BlockDeviceMappings', []))
                instance_data = f"{instance.get('InstanceId')}, {self.get_tag_name_from_tags(tags=tags, tag_name='Name')}, {instance.get('InstanceType')}, {instance_state}, {running_days}, {launch_time}"
                if cluster_tag in cluster_data:
                    if creation_date:
                        cluster_data[cluster_tag]['CreationDate'] = creation_date
                        cluster_data[cluster_tag]['ClusterState'] = instance_state
                        cluster_data[cluster_tag]['StoppedDate'] = stopped_date_time
                    cluster_data[cluster_tag]['Instances'].append(instance_data)
                    cluster_data[cluster_tag]['InstanceTypes'].append(instance.get('InstanceType'))
                    cluster_data[cluster_tag]['InstanceCount'] = len(cluster_data[cluster_tag]['Instances'])
                    cluster_data[cluster_tag]['Stopped'] = int(cluster_data[cluster_tag]['Stopped']) + stopped_instances
                    cluster_data[cluster_tag]['Running'] = int(cluster_data[cluster_tag]['Running']) + running_instances
                else:
                    cluster_data[cluster_tag] = {
                        'ClusterName': cluster_tag.split('/')[-1].upper(),
                        'ClusterName2': cluster_tag.split('/')[-1].lower(),
                        'ResourceId': cluster_tag,
                        'ClusterTag': cluster_tag,
                        'InstanceTypes': [instance.get('InstanceType')],
                        'User': self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                        'RunningDays': running_days,
                        'RunningHours': running_hours,
                        'RegionName': self._region,
                        'PublicCloud': self._cloud_name,
                        'Instances': [instance_data],
                        'LaunchTime': launch_time.date(),
                        'InstanceCount': 1,
                        'Stopped': stopped_instances,
                        'Running': running_instances,
                        'Graviton': using_graviton,
                        'RosaCluster': rosa_cluster,
                        'index-id': f'{datetime.datetime.now(datetime.timezone.utc).date()}-{self._cloud_name.lower()}-{self.account.lower()}-{self._region.lower()}-{cluster_tag}',
                    }
                    if creation_date:
                        cluster_data[cluster_tag]['creation_date'] = creation_date
                        cluster_data[cluster_tag]['ClusterState'] = instance_state
                        cluster_data[cluster_tag]['StoppedDate'] = stopped_date_time
        for cluster in cluster_data.values():
            instance_types = cluster['InstanceTypes']
            total_cost = 0
            graviton_instance_cost = 0
            cluster['GravitonInstanceTypes'] = []
            running_hours = 1 if cluster['RunningHours'] == 0 else cluster['RunningHours']
            for instance_type in set(instance_types):
                instance_types_count = instance_types.count(instance_type)
                unit_price = self._resource_pricing.get_ec2_price(region_name=self._region,
                                                                  instance_type=instance_type)
                total_cost += (unit_price * running_hours * instance_types_count)
                if not cluster['Graviton']:
                    instance_family, instance_size = instance_type.split('.')
                    graviton_instance = f'{DEFAULT_GRAVITON_INSTANCE}.{instance_size}'
                    if instance_family in GRAVITON_MAPPINGS:
                        graviton_instance = f'{GRAVITON_MAPPINGS[instance_family]}.{instance_size}'
                    graviton_unit_price = self._resource_pricing.get_ec2_price(region_name=self._region,
                                                                               instance_type=graviton_instance)
                    graviton_instance_cost += (graviton_unit_price * running_hours * instance_types_count)
                    cluster['GravitonInstanceTypes'].append(f"{graviton_instance}: {instance_types_count}")

            cluster['TotalGravitonInstanceCost'] = round(graviton_instance_cost, DEFAULT_ROUND_DIGITS)
            cluster['TotalCost'] = round(total_cost, DEFAULT_ROUND_DIGITS)

            cluster['GravitonSavings'] = round(total_cost - graviton_instance_cost,
                                               DEFAULT_ROUND_DIGITS) if graviton_instance_cost != 0 else 0
            cluster['InstanceTypes'] = [f"{x}: {instance_types.count(x)}" for x in set(instance_types)]
        return list(cluster_data.values())
