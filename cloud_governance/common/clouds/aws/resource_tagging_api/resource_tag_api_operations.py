import boto3

from cloud_governance.common.logger.init_logger import logger


class ResourceTagAPIOperations:
    """
    This class performs the resourcegrouptagapi operations
    """

    PAGINATION_TOKEN = 'PaginationToken'

    def __init__(self, region_name: str):
        self.__client = boto3.client('resourcegroupstaggingapi', region_name=region_name)

    def get_resources(self, tag_name: str, tag_value: str = ''):
        """
        This method returns all the resources having the tag_name and tag_value
        :return:
        """
        resources_list = []
        filters = {'Key': tag_name, 'Values': []}
        if tag_value:
            filters['Values'].append(tag_value)
        try:
            response = self.__client.get_resources(TagFilters=[filters])
            resources_list.extend(response['ResourceTagMappingList'])
            while response.get(self.PAGINATION_TOKEN):
                response = self.__client.get_resources(TagFilters=[filters],
                                                       PaginationToken=response.get(self.PAGINATION_TOKEN))
                resources_list.extend(response['ResourceTagMappingList'])
        except Exception as err:
            logger.error(err)
            raise err
        return resources_list

    def tag_resources(self, resource_arn_list: list, update_tags_dict: dict):
        """
        This method updates/tags list to the given resource arn's
        :param resource_arn_list:
        :param update_tags_dict:  {key: value}
        :return:
        """
        try:
            self.__client.tag_resources(ResourceARNList=resource_arn_list, Tags=update_tags_dict)
        except Exception as err:
            logger.error(err)
            raise err
