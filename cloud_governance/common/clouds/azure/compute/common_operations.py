from typing import Optional

from azure.core.paging import ItemPaged
from azure.identity import DefaultAzureCredential

from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables


class CommonOperations:

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self._default_creds = DefaultAzureCredential()
        self._subscription_id = self.__environment_variables_dict.get('AZURE_SUBSCRIPTION_ID')

    def _item_paged_iterator(self, item_paged_object: ItemPaged, as_dict: bool = False):
        """
        This method iterates the paged object and return the list
        :param item_paged_object:
        :return:
        """
        iterator_list = []
        try:
            page_item = item_paged_object.next()
            while page_item:
                if as_dict:
                    iterator_list.append(page_item.as_dict())
                else:
                    iterator_list.append(page_item)
                page_item = item_paged_object.next()
        except StopIteration:
            pass
        return iterator_list

    def check_tag_name(self, tags: Optional[dict], tag_name: str, cast_type: str = 'str'):
        """
        This method checks tag is present and return its value
        :param cast_type:
        :type cast_type:
        :param tags:
        :param tag_name:
        :return:
        """
        if tags:
            for key, value in tags.items():
                if string_equal_ignore_case(key, tag_name):
                    return self.__convert_cast_type(value=str(value), type_cast=cast_type)
        return ''

    def __convert_cast_type(self, type_cast: str, value: str):
        """
        This method returns the type conversion value
        :param type_cast:
        :type type_cast:
        :param value:
        :type value:
        :return:
        :rtype:
        """
        if type_cast == 'str':
            return str(value)
        elif type_cast == 'int':
            return int(value)
        elif type_cast == 'float':
            return float(value)
        else:
            return str(value)

    def get_resource_group_name_from_resource_id(self, resource_id: str):
        """
        This method returns the resource_group from resource_id
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        id_list = resource_id.split('/')
        key_values = {id_list[i].lower(): id_list[i+1] for i in range(0, len(id_list) - 1)}
        return key_values.get('resourcegroups').lower()

    def get_id_dict_data(self, resource_id: str):
        """
        This method generates the vm id dictionary
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        pairs = resource_id.split('/')[1:]
        key_pairs = {pairs[i].lower(): pairs[i + 1] for i in range(0, len(pairs), 2)}
        return key_pairs
