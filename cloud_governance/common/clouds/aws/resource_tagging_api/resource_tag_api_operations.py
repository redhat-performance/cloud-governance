import boto3

from cloud_governance.common.logger.init_logger import logger


class ResourceTagAPIOperations:
    """
    This class performs the resourcegrouptagapi operations
    """

    PAGINATION_TOKEN = 'PaginationToken'
    ARRAY_SIZE = 20

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
        chunked_array_list = [resource_arn_list[i:i + self.ARRAY_SIZE] for i in range(0, len(resource_arn_list),
                                                                                      self.ARRAY_SIZE)]
        for array_list in chunked_array_list:
            try:
                self.__client.tag_resources(ResourceARNList=array_list, Tags=update_tags_dict)
                logger.info(f"Updated the tags of the resources: {array_list} by tags: {update_tags_dict}")
            except Exception as err:
                logger.error(err)

    def tag_resources_by_tag_key_value(self, tags: dict, tag_key: str, tag_value: str = '', dry_run: str = 'yes'):
        """
        This method tags the resources based on tag_key and tag_value ( optional ) better to provide for easy filter
        :param tags:
        :type tags:
        :param tag_key:
        :type tag_key:
        :param tag_value:
        :type tag_value:
        :return:
        :rtype:
        """
        resources_arn = []
        resources = self.get_resources(tag_name=tag_key, tag_value=tag_value)
        for resource in resources:
            resources_arn.append(resource.get('ResourceARN'))
        if dry_run == 'no':
            self.tag_resources(resource_arn_list=resources_arn, update_tags_dict=tags)
        return resources_arn
