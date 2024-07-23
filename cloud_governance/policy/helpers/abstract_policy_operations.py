from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Union

from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.utils.configs import INSTANCE_IDLE_CPU_PERCENTAGE, INSTANCE_IDLE_NETWORK_IN_KILO_BYTES, \
    INSTANCE_IDLE_NETWORK_OUT_KILO_BYTES
from cloud_governance.common.utils.utils import Utils
from cloud_governance.common.elasticsearch.modals.policy_es_data import PolicyEsMetaData
from cloud_governance.main.environment_variables import environment_variables


class AbstractPolicyOperations(ABC):

    DAYS_TO_NOTIFY_ADMINS = 2
    DAYS_TO_TRIGGER_RESOURCE_MAIL = 4
    DAILY_HOURS = 24
    CURRENT_DATE = datetime.utcnow().date().__str__()

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self.account = self._environment_variables_dict.get('account')
        self._days_to_take_action = self._environment_variables_dict.get('DAYS_TO_TAKE_ACTION')
        self._dry_run = self._environment_variables_dict.get('dry_run')
        self._policy = self._environment_variables_dict.get('policy')
        self._force_delete = self._environment_variables_dict.get('FORCE_DELETE')
        self._resource_id = self._environment_variables_dict.get('RESOURCE_ID')
        self._es_upload = ElasticUpload()
        self._shutdown_period = self._environment_variables_dict.get('SHUTDOWN_PERIOD')

    def calculate_days(self, create_date: Union[datetime, str], start_date: Union[datetime, str] = datetime.utcnow()):
        """
        This method returns the days
        :param start_date:
        :type start_date:
        :param create_date:
        :type create_date:
        :return:
        :rtype:
        """
        if isinstance(create_date, str):
            create_date = datetime.strptime(create_date.split('T')[0], "%Y-%M-%d")
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.date()
        days = start_date - create_date.date()
        return days.days

    def get_clean_up_days_count(self, tags: Union[list, dict]):
        """
        This method returns the cleanup days count
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        if self._dry_run == 'yes':
            return 0
        last_used_day = self.get_tag_name_from_tags(tags=tags, tag_name='DaysCount')
        if not last_used_day:
            return 1
        else:
            date, days = last_used_day.split('@')
            if date != str(self.CURRENT_DATE):
                return int(days) + 1
            return 1 if int(days) == 0 else int(days)

    @abstractmethod
    def get_tag_name_from_tags(self, tags: Union[list, dict], tag_name: str):
        """
        This method returns the tag_value from the tags
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :return:
        :rtype:
        """
        raise NotImplementedError("This method is Not yet implemented")

    def get_skip_policy_value(self, tags: Union[list, dict]) -> str:
        """
        This method returns the skip value
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        policy_value = self.get_tag_name_from_tags(tags=tags, tag_name='Policy').strip()
        if not policy_value:
            policy_value = self.get_tag_name_from_tags(tags=tags, tag_name='Skip').strip()
        if policy_value:
            return policy_value.replace('_', '').replace('-', '').upper()
        return 'NA'

    @abstractmethod
    def _delete_resource(self, resource_id: str):
        """
        This method deletes the resource
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        raise NotImplementedError("This method is Not yet implemented")

    @abstractmethod
    def update_resource_day_count_tag(self, resource_id: str, cleanup_days: int, tags: list):
        """
        This method updates the resource tags
        :param resource_id:
        :type resource_id:
        :param cleanup_days:
        :type cleanup_days:
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        raise NotImplementedError("This method is Not yet implemented")

    def verify_and_delete_resource(self, resource_id: str, tags: Union[list, dict], clean_up_days: int,
                                   days_to_delete_resource: int = None, **kwargs):
        """
        This method verify and delete the resource by calculating the days
        :return:
        :rtype:
        """
        if self._resource_id == resource_id and self._force_delete and self._dry_run == 'no':
            self._delete_resource(resource_id=resource_id)
            return True
        if not days_to_delete_resource:
            days_to_delete_resource = self._days_to_take_action
        cleanup_resources = False
        if clean_up_days >= self._days_to_take_action - self.DAYS_TO_TRIGGER_RESOURCE_MAIL:
            if clean_up_days == self._days_to_take_action - self.DAYS_TO_TRIGGER_RESOURCE_MAIL:
                kwargs['delta_cost'] = kwargs.get('extra_purse')
                # @Todo, If it require add email alert. May In future will add the email alert.
            else:
                if clean_up_days >= days_to_delete_resource:
                    if self._dry_run == 'no':
                        if self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP'):
                            self._delete_resource(resource_id=resource_id)
                            cleanup_resources = True
        return cleanup_resources

    @abstractmethod
    def _update_tag_value(self, tags: Union[list, dict], tag_name: str, tag_value: str):
        """
        This method returns the updated tag_list by adding the tag_name and tag_value to the tags
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :param tag_value:
        :type tag_value:
        :return:
        :rtype:
        """
        raise NotImplementedError("This method is Not yet implemented")

    @abstractmethod
    def _get_all_instances(self):
        """
        This method returns all the instances
        :return:
        :rtype:
        """
        raise NotImplementedError("This method not yet implemented")

    @abstractmethod
    def _get_all_volumes(self):
        """
        This method returns all the volumes
        :return:
        :rtype:
        """
        raise NotImplementedError("This method not yet implemented")

    def __current_savings_year(self, unit_price: float):
        """
        This method returns the savings this year
        :param unit_price:
        :type unit_price:
        :return:
        :rtype:
        """
        year_end_date = datetime.now(timezone.utc).date().replace(month=12, day=31)
        total_days = (year_end_date - datetime.now(timezone.utc).date()).days + 1
        return total_days * 24 * unit_price

    # ES Schema format
    def _get_es_schema(self, **kwargs):
        kwargs['expire_days'] = self._days_to_take_action
        kwargs['region_name'] = kwargs.pop('region', '')
        kwargs['resource_action'] = kwargs.pop('cleanup_result', '')
        kwargs['public_cloud'] = kwargs.pop('cloud_name', '')
        kwargs['clean_up_days'] = kwargs.get('cleanup_days', 0)
        kwargs['days_count'] = kwargs.pop('cleanup_days', 0)
        kwargs['account'] = self.account
        kwargs['total_yearly_savings'] = self.__current_savings_year(unit_price=kwargs.get('unit_price', 0))
        policy_es_data = PolicyEsMetaData(**kwargs)
        resource_data = policy_es_data.get_as_dict_title_case()
        return resource_data

    @abstractmethod
    def run_policy_operations(self):
        """
        This method returns policy output
        :return:
        :rtype:
        """
        pass

    def run(self):
        """
        This method starts the policy operations
        :return:
        :rtype:
        """
        return self.run_policy_operations()

    def verify_instance_idle(self, resource_id: str):
        """
        This method returns the metrics of the resource
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        cpu_percentage = self.get_cpu_utilization_percentage_metric(resource_id)
        network_in_kilobytes = self.get_network_in_kib_metric(resource_id)
        network_out_kilobytes = self.get_network_out_kib_metric(resource_id)
        return Utils.less_than(cpu_percentage, INSTANCE_IDLE_CPU_PERCENTAGE) and \
            Utils.less_than(network_in_kilobytes, INSTANCE_IDLE_NETWORK_IN_KILO_BYTES) and \
            Utils.less_than(network_out_kilobytes, INSTANCE_IDLE_NETWORK_OUT_KILO_BYTES)

    def get_cpu_utilization_percentage_metric(self, resource_id: str, **kwargs):
        """
        This method returns the cpu utilization percentage
        :param resource_id:
        :type resource_id:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        raise NotImplementedError("Not implemented error")

    def get_network_in_kib_metric(self, resource_id: str, **kwargs):
        """
        This method returns the total Network In KiB
        :param resource_id:
        :type resource_id:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        raise NotImplementedError("Not implemented error")

    def get_network_out_kib_metric(self, resource_id: str, **kwargs):
        """
        This method returns the total Network Out KiB
        :param resource_id:
        :type resource_id:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        raise NotImplementedError("Not implemented error")
