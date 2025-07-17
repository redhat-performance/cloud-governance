from azure.mgmt.resource import ResourceManagementClient
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.clouds.azure.subscriptions.azure_operations import AzureOperations


class TagAzureResourceGroup:
    def __init__(self):
        """
        Initialize Azure clients and set the tags to apply.
        :param tags_to_add: Dictionary of tags to add to resource groups and their resources.
        """
        self.azure_operations = AzureOperations()
        self.subscription_id = self.azure_operations.subscription_id
        self.credential = self.azure_operations._AzureOperations__default_creds  # reuse credentials
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        self.tags_to_add = self.azure_operations.global_tags

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
                    parameters={"tags": self.tags_to_add}
                )
                logger.info(f"Tagged resource group: {rg.name}")
            except Exception as e:
                logger.error(f"Failed to tag resource group {rg.name}: {e}")
                continue

            # Tag all resources in the resource group
            for resource in self.resource_client.resources.list_by_resource_group(rg.name):
                logger.info(f"  Tagging resource: {resource.name} ({resource.type})")

                existing_tags = resource.tags or {}
                updated_tags = {**existing_tags, **self.tags_to_add}

                try:
                    provider_ns, resource_type_str = resource.type.split('/')
                    provider = self.resource_client.providers.get(provider_ns)
                    resource_type_info = next(
                        rt for rt in provider.resource_types if rt.resource_type.lower() == resource_type_str.lower()
                    )
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
                    logger.info(f"    Tagged resource: {resource.name}")
                except Exception as e:
                    logger.error(f"    Failed to tag resource {resource.name}: {e}")

    def run(self):
        """
        This method tags all Azure resources.
        """
        self.tag_all()
