from abc import ABC

import typeguard

from cloud_governance.cloud_resource_orchestration.clouds.common.abstract_tagging_operations import \
    AbstractTaggingOperations
from cloud_governance.common.clouds.aws.resource_tagging_api.resource_tag_api_operations import ResourceTagAPIOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class AWSTaggingOperations(AbstractTaggingOperations):
    """
    This class is performs the tagging operations on AWS
    """

    def __init__(self, region_name: str):
        super(AbstractTaggingOperations).__init__()
        self.__resource_tag_api_operations = ResourceTagAPIOperations(region_name=region_name)

    @logger_time_stamp
    def tag_resources_list(self, resources_list: list, update_tags_dict: dict):
        """
        This method updates the tags to the resources
        :param resources_list:
        :param update_tags_dict:
        :return:
        """
        self.__resource_tag_api_operations.tag_resources(resource_arn_list=resources_list,
                                                         update_tags_dict=update_tags_dict)

    @typeguard.typechecked
    @logger_time_stamp
    def get_resources_list(self, tag_name: str, tag_value: str = ''):
        """
        This method returns all the resources having the tag_name and tag_value
        :param tag_name:
        :param tag_value:
        :return:
        """
        resources_list = self.__resource_tag_api_operations.get_resources(tag_name=tag_name, tag_value=tag_value)
        if resources_list:
            return resources_list
        return []
