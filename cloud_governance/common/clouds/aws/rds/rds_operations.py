from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class RDSOperations:
    """
    This class performs the RDS operations
    """

    def __init__(self, region_name: str):
        self._db_client = get_boto3_client('rds', region_name=region_name)

    def describe_db_instances(self, **kwargs):
        """
        This method returns the rds databases
        :return:
        :rtype:
        """
        rds_instances = []
        try:
            rds_instances = Utils.iter_client_function(func_name=self._db_client.describe_db_instances,
                                                       output_tag='DBInstances',
                                                       iter_tag_name='Marker', **kwargs)
        except Exception as err:
            logger.error(f"Can't describe the rds instances: {err}")
        return rds_instances

    def add_tags_to_resource(self, resource_arn: str, tags: list):
        """
        This method add/ update the tags to the database
        :param resource_arn:
        :type resource_arn:
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        try:
            self._db_client.add_tags_to_resource(ResourceName=resource_arn, Tags=tags)
            logger.info(f"Tags are updated to the resource: {resource_arn}")
        except Exception as err:
            logger.error(f"Something went wrong in add/ update tags: {err}")

    def remove_tags_from_resource(self, resource_arn: str, tags: list):
        """
        This method deletes the tags of the rds resource
        :param resource_arn:
        :param tags:
        :return:
        """
        try:
            tags_keys = [key for tag in tags for key, _ in tag.items() if key == 'Key']
            self._db_client.remove_tags_from_resource(ResourceName=resource_arn, Tags=tags_keys)
            logger.info(f"Tags: {tags_keys} are deleted to the resource: {resource_arn}")
        except Exception as err:
            logger.error(f"Something went wrong in add/ update tags: {err}")
