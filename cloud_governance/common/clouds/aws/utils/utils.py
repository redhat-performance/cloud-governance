from typing import Callable

import boto3
import typeguard

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class Utils:
    """
    This is global methods
    """

    def __init__(self, region: str = 'us-east-2'):
        self.region = region
        pass

    @typeguard.typechecked
    def get_details_resource_list(self, func_name: Callable, input_tag: str, check_tag: str):
        """
        This method fetch all Items of the resource i.e: EC2, IAM
        :param func_name:
        :param input_tag:
        :param check_tag:
        :return:
        """
        resource_list = []
        resources = func_name()
        resource_list.extend(resources[input_tag])
        while check_tag in resources.keys():
            if check_tag == 'NextToken':
                resources = func_name(NextToken=resources[check_tag])
            elif check_tag == 'Marker':
                resources = func_name(Marker=resources[check_tag])
            resource_list.extend(resources[input_tag])
        return resource_list
