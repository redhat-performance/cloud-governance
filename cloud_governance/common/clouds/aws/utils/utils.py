from typing import Callable

import typeguard

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class Utils:
    """
    This is global methods
    """

    def __init__(self, region: str = 'us-east-2'):
        self.region = region
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__update_tag_bulks = self.__environment_variables_dict.get('UPDATE_TAG_BULKS')

    @typeguard.typechecked
    def get_details_resource_list(self, func_name: Callable, input_tag: str, check_tag: str, **kwargs):
        """
        This method fetch all Items of the resource i.e: EC2, IAM
        :param func_name:
        :param input_tag:
        :param check_tag:
        :return:
        """
        resource_list = []
        resources = func_name(**kwargs)
        resource_list.extend(resources[input_tag])
        while check_tag in resources.keys():
            if check_tag == 'NextToken':
                resources = func_name(NextToken=resources[check_tag], **kwargs)
            elif check_tag == 'Marker':
                resources = func_name(Marker=resources[check_tag], **kwargs)
            resource_list.extend(resources[input_tag])
        return resource_list

    @logger_time_stamp
    def __tag_resources(self, client_method: Callable, resource_ids: list, tags: list, tags_name: str = 'Tags'):
        """
        This method tag resources
        :param client_method:
        :param resource_ids:
        :param tags:
        :param tags_name:
        :return:
        """
        if tags_name == 'Tags':
            client_method(Resources=resource_ids, Tags=tags)

    @logger_time_stamp
    def __split_run_bulks(self, iterable: list, limit: int = 1):
        """
        This method splits run into bulk depends on threads limit
        @return: run bulks
        """
        result = []
        length = len(iterable)
        for ndx in range(0, length, limit):
            result.append(iterable[ndx:min(ndx + limit, length)])
        return result

    @typeguard.typechecked
    @logger_time_stamp
    def tag_aws_resources(self, client_method: Callable, tags: list, resource_ids: list):
        """
        This method tag the aws resources with batch wise of 20
        :param client_method:
        :param tags:
        :param resource_ids:
        :return:
        """
        if tags:
            bulk_resource_ids_list = self.__split_run_bulks(iterable=resource_ids, limit=self.__update_tag_bulks)  # split the aws resource_ids into batches
            co = 0
            cpu_based_resource_ids_list = self.__split_run_bulks(iterable=bulk_resource_ids_list, limit=self.__update_tag_bulks)
            for cpu_based_resource_ids_list in cpu_based_resource_ids_list:
                for resource_ids_list in cpu_based_resource_ids_list:
                    self.__tag_resources(client_method, resource_ids_list, tags)
                    co += 1
            return co

    @staticmethod
    @typeguard.typechecked
    def iter_client_function(func_name: Callable, output_tag: str, iter_tag_name: str, **kwargs):
        """
        This method fetch all Items of the resource i.e: EC2, IAM
        :param func_name:
        :param output_tag:
        :param iter_tag_name:
        :return:
        """
        resource_list = []
        resources = func_name(**kwargs)
        resource_list.extend(resources[output_tag])
        while iter_tag_name in resources.keys():
            if iter_tag_name == 'NextToken':
                resources = func_name(NextToken=resources[iter_tag_name], **kwargs)
            elif iter_tag_name == 'Marker':
                resources = func_name(Marker=resources[iter_tag_name], **kwargs)
            resource_list.extend(resources[output_tag])
        return resource_list
