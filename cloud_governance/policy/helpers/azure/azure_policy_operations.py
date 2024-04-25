import json
from datetime import datetime, timedelta

from cloud_governance.common.clouds.azure.compute.compute_operations import ComputeOperations
from cloud_governance.common.clouds.azure.compute.network_operations import NetworkOperations
from cloud_governance.common.clouds.azure.compute.resource_group_operations import ResourceGroupOperations
from cloud_governance.common.clouds.azure.monitor.monitor_management_operations import MonitorManagementOperations
from cloud_governance.common.utils.configs import INSTANCE_IDLE_DAYS, DEFAULT_ROUND_DIGITS, TOTAL_BYTES_IN_KIB
from cloud_governance.policy.helpers.abstract_policy_operations import AbstractPolicyOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.utils import Utils


class AzurePolicyOperations(AbstractPolicyOperations):

    def __init__(self):
        self._cloud_name = 'Azure'
        self.compute_operations = ComputeOperations()
        self.network_operations = NetworkOperations()
        self.resource_group_operations = ResourceGroupOperations()
        self.monitor_operations = MonitorManagementOperations()
        super().__init__()

    def get_tag_name_from_tags(self, tags: dict, tag_name: str):
        """
        This method returns the tag value by the tag_name
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :return:
        :rtype:
        """
        if tags:
            for key, value in tags.items():
                if Utils.equal_ignore_case(key, tag_name):
                    return value
        return ''

    def _delete_resource(self, resource_id: str):
        """
        This method deletes the
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        action = "deleted"
        try:
            if self._policy in ['instance_run', 'instance_idle']:
                action = "Stopped"
                delete_status = self.compute_operations.stop_vm(resource_id=resource_id)
            elif self._policy == 'unattached_volume':
                delete_status = self.compute_operations.delete_disk(resource_id=resource_id)
            elif self._policy == 'ip_unattached':
                delete_status = self.network_operations.release_public_ip(resource_id=resource_id)
            elif self._policy == 'unused_nat_gateway':
                delete_status = self.network_operations.delete_nat_gateway(resource_id=resource_id)
            logger.info(f'{self._policy} {action}: {resource_id}')
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def update_resource_day_count_tag(self, resource_id: str, cleanup_days: int, tags: dict):
        tags = self._update_tag_value(tags=tags, tag_name='DaysCount', tag_value=str(cleanup_days))
        try:
            if self._policy in ['instance_run', 'unattached_volume', 'ip_unattached', 'unused_nat_gateway']:
                self.resource_group_operations.creates_or_updates_tags(resource_id=resource_id, tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def _update_tag_value(self, tags: dict, tag_name: str, tag_value: str):
        """
        This method returns the updated tag_list by adding the tag_name and tag_value to the tags
        @param tags:
        @param tag_name:
        @param tag_value:
        @return:
        """
        if not tags:
            tags = {}
        if self._dry_run == "yes":
            tag_value = 0
        tag_value = f'{self.CURRENT_DATE}@{tag_value}'
        found = False
        updated_tags = {}
        if tags:
            for key, value in tags.items():
                if Utils.equal_ignore_case(key, tag_name):
                    if value.split("@")[0] != self.CURRENT_DATE:
                        updated_tags[key] = tag_value
                    else:
                        if int(tag_value.split("@")[-1]) == 0 or int(tag_value.split("@")[-1]) == 1:
                            updated_tags[key] = tag_value
                    found = True
        tags.update(updated_tags)
        if not found:
            tags.update({tag_name: tag_value})
        return tags

    def _get_all_instances(self):
        """
        This method returns the all instances list
        :return:
        :rtype:
        """
        return self.compute_operations.get_all_instances()

    def run_policy_operations(self):
        raise NotImplementedError("This method needs to be implemented")

    def _get_all_volumes(self) -> list:
        """
        This method returns the volumes by state
        :return:
        :rtype:
        """
        volumes = self.compute_operations.get_all_disks()
        return volumes

    def _get_active_cluster_ids(self):
        """
        This method returns the active cluster id's
        :return:
        :rtype:
        """
        active_instances = self._get_all_instances()
        cluster_ids = []
        for vm in active_instances:
            tags = vm.tags if vm.tags else {}
            for key, value in tags.items():
                if key.startswith('kubernetes.io/cluster'):
                    cluster_ids.append(key)
                    break
        return cluster_ids

    def _get_cluster_tag(self, tags: dict):
        """
        This method returns the cluster_tag
        :return:
        :rtype:
        """
        if tags:
            for key, value in tags.items():
                if key.startswith('kubernetes.io/cluster'):
                    return key
        return ''

    def _get_instance_status(self, resource_id: str, vm_name: str):
        """
        This method returns the VM status of the Virtual Machine
        :param resource_id:
        :type resource_id:
        :param vm_name:
        :type vm_name:
        :return:
        :rtype:
        """
        instance_statuses = self.compute_operations.get_instance_statuses(resource_id=resource_id, vm_name=vm_name)
        statuses = instance_statuses.get('statuses', {})
        if len(statuses) >= 2:
            status = statuses[1].get('display_status', '').lower()
        elif len(statuses) == 1:
            status = statuses[0].get('display_status', '').lower()
        else:
            status = 'Unknown Status'
        return status

    def __get_aggregation_metrics_value(self, metrics: dict, aggregation: str):
        """
        This method returns the aggregation value of the metrics
        :param metrics:
        :type metrics:
        :param aggregation:
        :type aggregation:
        :return:
        :rtype:
        """
        total_metrics = 0
        metric_aggregation_value = 0
        for metric in metrics.get('value', []):
            metrics_data = metric.get('timeseries', [])
            if metrics_data:
                total_metrics = len(metrics_data[0].get('data', []))
                for metric_data in metrics_data[0].get('data', []):
                    metric_aggregation_value += metric_data.get(aggregation)
        if Utils.equal_ignore_case(aggregation, 'average'):
            return round(metric_aggregation_value / total_metrics, DEFAULT_ROUND_DIGITS)
        else:
            return round(metric_aggregation_value, DEFAULT_ROUND_DIGITS)

    def get_cpu_utilization_percentage_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS):
        """
        This method returns the cpu utilization percentage
        :param days:
        :type days:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        timespan = f'{start_date}/{end_date}'
        cpu_metrics = self.monitor_operations.get_resource_metrics(resource_id=resource_id,
                                                                   metricnames='Percentage CPU',
                                                                   aggregation='Average',
                                                                   timespan=timespan)
        average_cpu_metrics_value = self.__get_aggregation_metrics_value(metrics=cpu_metrics, aggregation='average')
        return average_cpu_metrics_value

    def get_network_in_kib_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS):
        """
        This method returns the total Network In KiB
        :param days:
        :type days:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        timespan = f'{start_date}/{end_date}'
        network_in_metrics = self.monitor_operations.get_resource_metrics(resource_id=resource_id,
                                                                          metricnames='Network In Total',
                                                                          aggregation='Average',
                                                                          timespan=timespan)
        average_network_in_bytes = self.__get_aggregation_metrics_value(metrics=network_in_metrics,
                                                                        aggregation='average')
        return round(average_network_in_bytes / TOTAL_BYTES_IN_KIB, DEFAULT_ROUND_DIGITS)

    def get_network_out_kib_metric(self, resource_id: str, days: int = INSTANCE_IDLE_DAYS):
        """
        This method returns the total Network Out KiB
        :param days:
        :type days:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        start_date, end_date = Utils.get_start_and_end_datetime(days=days)
        timespan = f'{start_date}/{end_date}'
        network_out_metrics = self.monitor_operations.get_resource_metrics(resource_id=resource_id,
                                                                           metricnames='Network Out Total',
                                                                           aggregation='Average',
                                                                           timespan=timespan)
        average_network_out_bytes = self.__get_aggregation_metrics_value(metrics=network_out_metrics,
                                                                         aggregation='average')
        return round(average_network_out_bytes / TOTAL_BYTES_IN_KIB, DEFAULT_ROUND_DIGITS)
