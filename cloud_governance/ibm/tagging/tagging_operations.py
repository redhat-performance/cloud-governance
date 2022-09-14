import os
from ast import literal_eval

from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount
from cloud_governance.common.clouds.ibm.classic.classic_operations import ClassicOperations


class TaggingOperations:
    """
    This class contain common methods and parameters required for tagging ibm baremetal, vm
    """

    def __init__(self):
        self._ibm_client = IBMAccount()
        self._sl_client = self._ibm_client.get_sl_client()
        self._classic_operations = ClassicOperations()
        self._dry_run = os.environ.get('dry_run', 'yes')
        self._tag_operation = os.environ.get('tag_operation', 'read')
        self._tag_remove_name = os.environ.get('tag_remove_name', '')
        self._tag_custom = self.__get_literal_eval(os.environ.get('tag_custom', '[]'))

    def __get_literal_eval(self, env_input: any):
        return literal_eval(env_input)

    def _filter_common_tags(self, user_tags: list, resource_tags: list):
        """
        This method filter the common tags form the resource tags to user tags
        @param user_tags:
        @param resource_tags:
        @return:
        """
        tags = []
        for tag in user_tags:
            if tag not in resource_tags:
                tags.append(tag)
        return tags

    def _filter_remove_tags(self, user_tags: list, resource_tags: list):
        """
        This method filter the remove tags from use_tags to resource_tags
        @param user_tags:
        @param resource_tags:
        @return:
        """
        remove_tags = []
        for tag in user_tags:
            if tag in resource_tags:
                remove_tags.append(tag)
        return remove_tags

    def softlayer_operation(self, softlayer_name: str, softlayer_method: str, resource_id: str, tags: str):
        """
        This method takes softlayer name and its method
        @param softlayer_name:
        @param softlayer_method:
        @param resource_id:
        @param tags:
        @return:
        """
        return self._sl_client.call(softlayer_name,softlayer_method, tags, id=resource_id)
