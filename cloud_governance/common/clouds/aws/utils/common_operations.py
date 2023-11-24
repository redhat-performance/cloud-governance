from typing import Callable

from cloud_governance.exceptions.clouds.aws_exceptions import AWSPaginationVariableNotFound


def iterate_next_token(function: Callable, output_identifier: str, marker: str = 'NextToken', **kwargs):
    """
    This method iterate over the function using the marker and return the result
    :param function:
    :param output_identifier:
    :param marker:
    :return:
    """
    if marker in ('NextToken', 'Marker'):
        resources_list = []
        resources = function(**kwargs)
        resources_list.extend(resources[output_identifier])
        if 'Marker' in resources.keys():
            marker = 'Marker'
        if 'NextToken' in resources.keys():
            marker = 'NextToken'
        while marker in resources.keys():
            if marker == 'NextToken':
                resources = function(NextToken=resources[marker], **kwargs)
            elif marker == 'Marker':
                resources = function(Marker=resources[marker], **kwargs)
            resources_list.extend(resources[output_identifier])
        return resources_list
    else:
        raise AWSPaginationVariableNotFound("Accepted values are: NextToken, Marker")


def get_tag_name_and_value(tags: list, key: str, check_prefix: bool = False):
    """
    This method returns the tag_key and tag_value, the operations would be case-insensitive
    :param tags:
    :type tags:
    :param key:
    :type key:
    :param check_prefix:
    :type check_prefix:
    :return:
    :rtype:
    """
    for tag in tags:
        if check_prefix:
            if key.lower() in tag.get('Key').lower():
                return tag.get('Key'), tag.get('Value')
        else:
            if key.lower() == tag.get('Key').lower():
                return tag.get('Key'), tag.get('Value')
    return '', ''


def convert_key_values_to_dict(tags: list):
    """
    This method convert aws key values to dict
    :param tags:
    :type tags:
    :return:
    :rtype:
    """
    tags_dict = {}
    if tags:
        for tag in tags:
            tags_dict.update({tag.get('Key'): tag.get('Value')})
    return tags_dict


def convert_dict_to_key_values(tags: dict):
    """
    This method convert dict to aws key values
    :param tags:
    :type tags:
    :return:
    :rtype:
    """
    key_values = []
    if tags:
        for key, value in tags.items():
            key_values.append({'Key': key, 'Value': value})
    return key_values
