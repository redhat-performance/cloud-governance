import boto3

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.configs import AWS_DEFAULT_GLOBAL_REGION


def get_tag_value_from_tags(tags: list, tag_name: str, cast_type: str = 'str',
                            default_value: any = '') -> any:
    """
    This method returns the tag value inputted by tag_name
    :param tags:
    :type tags:
    :param tag_name:
    :type tag_name:
    :param cast_type:
    :type cast_type:
    :param default_value:
    :type default_value:
    :return:
    :rtype:
    """
    if tags:
        for tag in tags:
            key = tag.get('Key').lower().replace("_", '').replace("-", '').strip()
            if key == tag_name.lower():
                if cast_type:
                    if cast_type == 'int':
                        return int(tag.get('Value').split()[0].strip())
                    elif cast_type == 'float':
                        return float(tag.get('Value').strip())
                    else:
                        return str(tag.get('Value').strip())
                return tag.get('Value').strip()
    return default_value


def get_boto3_client(client: str, region_name: str = AWS_DEFAULT_GLOBAL_REGION, **kwargs):
    """
    This method initializes the aws boto3 client
    :param client:
    :type client:
    :param region_name:
    :type region_name:
    :return:
    :rtype:
    """
    client_object = None
    try:
        client_object = boto3.client(client, region_name=region_name, **kwargs)
    except Exception as err:
        logger.error(f"{client} Client Initialization error: {err}")
    return client_object
