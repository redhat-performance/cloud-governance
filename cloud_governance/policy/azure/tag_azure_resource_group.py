from azure.mgmt.resource import ResourceManagementClient
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations


class TagAzureResourceGroup:
    def __init__(self):
        """
        Initialize Azure clients and set the tags to apply.
        """
        self.__azure_operations = AzureOperations()
        self.__subscription_id = self.__azure_operations.subscription_id
        self.__credential = self.__azure_operations._AzureOperations__default_creds  # reuse credentials
        self.resource_client = ResourceManagementClient(self.__credential, self.__subscription_id)
        self.__tags_to_add = self.__azure_operations.global_tags
        if not self.__tags_to_add:
            raise ValueError("No tags provided to add. Please set GLOBAL_TAGS environment variable.")

    def tag_all(self):
        """
        Tag all resource groups and their contained resources with the specified tags.
        """
        resource_groups = self.resource_client.resource_groups.list()

        for rg in resource_groups:
            logger.info(f"Processing resource group: {rg.name}")
            # Tag the resource group
            try:
                self.resource_client.resource_groups.update(
                    resource_group_name=rg.name,
                    parameters={"tags": self.__tags_to_add}
                )
                logger.info(f"Tagged resource group: {rg.name}")
            except Exception as e:
                logger.error(f"Failed to tag resource group {rg.name}: {e}")
                continue

            # Tag all resources in the resource group
            for resource in self.resource_client.resources.list_by_resource_group(rg.name):
                logger.info(f"Tagging resource: {resource.name} ({resource.type})")

                existing_tags = resource.tags or {}
                updated_tags = {**existing_tags, **self.__tags_to_add}

                try:
                    parts = resource.type.split('/')
                    provider_ns = parts[0]
                    resource_type_str = '/'.join(parts[1:])

                    provider = self.resource_client.providers.get(provider_ns)

                    # Some resource_type may not match exactly, use a relaxed matching
                    resource_type_info = next(
                        (rt for rt in provider.resource_types if rt.resource_type.lower() == resource_type_str.lower()),
                        None
                    )

                    if not resource_type_info:
                        logger.warning(f"Could not find exact match for resource type: {resource_type_str} in provider {provider_ns}")
                        continue

                    api_version = next(
                        (v for v in resource_type_info.api_versions if 'preview' not in v.lower()),
                        resource_type_info.api_versions[0]
                    )

                    poller = self.resource_client.resources.begin_update_by_id(
                        resource_id=resource.id,
                        api_version=api_version,
                        parameters={
                            'location': resource.location,
                            'tags': updated_tags
                        }
                    )
                    poller.result()
                    logger.info(f"Tagged resource: {resource.name}")
                except Exception as e:
                    logger.error(f"Failed to tag resource {resource.name}: {e}")

    def run(self):
        """
        This method tags all Azure resources.
        """
        self.tag_all()
