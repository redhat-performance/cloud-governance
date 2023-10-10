

import typeguard

from cloud_governance.cloud_resource_orchestration.clouds.common.abstract_tagging_operations import \
    AbstractTaggingOperations
from cloud_governance.common.clouds.azure.compute.resource_group_operations import ResourceGroupOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class AzureTaggingOperations(AbstractTaggingOperations):
    """
    This class performs the tagging operations on AWS
    """

    def __init__(self):
        super(AbstractTaggingOperations).__init__()
        self.__resource_group_operations = ResourceGroupOperations()

    @logger_time_stamp
    def tag_resources_list(self, resources_list: list, update_tags_dict: dict):
        """
        This method updates the tags to the resources
        :param resources_list:
        :param update_tags_dict:
        :return:
        """
        pass

    @typeguard.typechecked
    @logger_time_stamp
    def get_resources_list(self, tag_name: str, tag_value: str = ''):
        """
        This method returns all the resources having the tag_name and tag_value
        :param tag_name:
        :param tag_value:
        :return:
        """
        filter_values = f"``$filter=tagName eq '{tag_name}' and tagValue eq '{tag_value}'``"
        return self.__resource_group_operations.get_all_resources(filter=filter_values)
