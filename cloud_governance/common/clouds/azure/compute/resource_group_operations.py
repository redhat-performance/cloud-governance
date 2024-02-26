import typeguard
from azure.core.paging import ItemPaged
from azure.core.polling import LROPoller
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.v2022_09_01.models import ResourceGroup, GenericResourceExpanded, TagsResource, Tags

from cloud_governance.common.clouds.azure.common.common_operations import CommonOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class ResourceGroupOperations(CommonOperations):

    def __init__(self):
        super().__init__()
        self.__resource_client = ResourceManagementClient(self._default_creds, subscription_id=self._subscription_id)

    @logger_time_stamp
    def get_all_resource_groups(self, **kwargs) -> [ResourceGroup]:
        """
        This method returns all resource groups present in azure subscription
        :return:
        """
        resource_groups_object: ItemPaged = self.__resource_client.resource_groups.list(**kwargs)
        resource_groups_list = self._item_paged_iterator(item_paged_object=resource_groups_object)
        return resource_groups_list

    @typeguard.typechecked
    @logger_time_stamp
    def get_all_resources(self, resource_group_name: str) -> [GenericResourceExpanded]:
        """
        This method returns all the resources in a resource_group
        :param resource_group_name:
        :type resource_group_name:
        :return:
        :rtype:
        """
        resources_list_object: ItemPaged = self.__resource_client.resources.list_by_resource_group(resource_group_name=resource_group_name)
        resources_list = self._item_paged_iterator(item_paged_object=resources_list_object)
        return resources_list

    def creates_or_updates_tags(self, resource_id: str, tags: dict):
        """
        This method creates or updates the tag on the specific resource
        :param tags:
        :param resource_id:
        :return:
        """
        status: LROPoller = self.__resource_client.tags.begin_create_or_update_at_scope(scope=resource_id,
                                                                                        parameters=self.__construct_tags(tags=tags))
        return status.done()

    def __construct_tags(self, tags: dict) -> TagsResource:
        """
        This method constructs the tags
        :param tags:
        :return:
        """
        tag_resource = TagsResource(properties=Tags(tags=tags))

        return tag_resource
