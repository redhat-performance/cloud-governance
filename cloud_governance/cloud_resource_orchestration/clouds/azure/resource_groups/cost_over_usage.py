from abc import ABC
from datetime import datetime

from cloud_governance.cloud_resource_orchestration.clouds.common.abstract_cost_over_usage import AbstractCostOverUsage
from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.common.clouds.azure.compute.compute_operations import ComputeOperations
from cloud_governance.common.clouds.azure.cost_management.cost_management_operations import CostManagementOperations


class CostOverUsage(AbstractCostOverUsage, ABC):

    def __init__(self):
        super().__init__()
        self.__cost_mgmt_operations = CostManagementOperations()
        self.__compute_operations = ComputeOperations()
        self._subscription_id = self._environment_variables_dict.get('AZURE_SUBSCRIPTION_ID')
        self.__scope = f'subscriptions/{self._subscription_id}'

    def get_cost_management_object(self):
        """
        This method returns the object of cost_mgmt
        :return:
        :rtype:
        """
        return self.__cost_mgmt_operations

    def _verify_active_resources(self, tag_name: str, tag_value: str) -> bool:
        """
        This method verifies any active virtual instances in all regions by tag_name, tag_value
        :param tag_name:
        :type tag_name:
        :param tag_value:
        :type tag_value:
        :return:
        :rtype:
        """
        virtual_machines = self.__compute_operations.get_all_instances()
        for virtual_machine in virtual_machines:
            tags = virtual_machine.tags
            user = self.__compute_operations.check_tag_name(tags=tags, tag_name=tag_name)
            if string_equal_ignore_case(user, tag_value):
                return True
        return False

    def _get_cost_based_on_tag(self, start_date: str, end_date: str, tag_name: str, extra_filters: any = None,
                               extra_operation: str = 'And', granularity: str = None, forecast: bool = False, **kwargs):
        """
        This method returns the cost results based on the tag_name
        :param start_date:
        :type start_date:
        :param end_date:
        :type end_date:
        :param tag_name:
        :type tag_name:
        :param extra_filters:
        :type extra_filters:
        :param extra_operation:
        :type extra_operation:
        :param granularity:
        :type granularity:
        :param forecast:
        :type forecast:
        :return:
        :rtype:
        """
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        if forecast:
            # Todo complete the forecast function
            results_by_time = self.__cost_mgmt_operations.get_forecast(start_date=start_date, end_date=end_date,
                                                                       granularity=granularity,
                                                                       grouping=['user'],
                                                                       scope=self.__scope, **kwargs
                                                                       )
        else:
            results_by_time = self.__cost_mgmt_operations.get_usage(scope=self.__scope, start_date=start_date,
                                                                    end_date=end_date, grouping=[tag_name],
                                                                    granularity=granularity, **kwargs)

            response = self.__cost_mgmt_operations.get_filter_data(cost_data=results_by_time, tag_name=tag_name)
            return response
        return {}
