from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union

from cloud_governance.main.environment_variables import environment_variables


class AbstractCleanUpOperations(ABC):

    DAYS_TO_NOTIFY_ADMINS = 2
    DAYS_TO_TRIGGER_RESOURCE_MAIL = 4
    DAILY_HOURS = 24
    CURRENT_DATE = datetime.utcnow().date().__str__()

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._days_to_take_action = self._environment_variables_dict.get('DAYS_TO_TAKE_ACTION')
        self._dry_run = self._environment_variables_dict.get('dry_run')
        self._policy = self._environment_variables_dict.get('policy')
        self._force_delete = self._environment_variables_dict.get('FORCE_DELETE')
        self._resource_id = self._environment_variables_dict.get('RESOURCE_ID')

    @abstractmethod
    def get_clean_up_days_count(self, tags: Union[list, dict]):
        """
        This method returns the cleanup days count
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        raise NotImplementedError("This method is Not yet implemented")

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

    def verify_and_delete_resource(self, resource_id: str, tags: list, clean_up_days: int,
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
