from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.monitor_cro_resources import \
    MonitorCROResources
from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.tag_cro_resources import TagCROResources


class AzureRunCro:

    def __init__(self):
        pass

    def __run_cloud_resources(self):
        """
        This method run the azure resources in specified region or all regions
        :return:
        """
        TagCROResources().run()
        monitored_resources = MonitorCROResources().run()

    def __start_cro(self):
        """
        This method start the cro process methods
        1. Send alert to cost over usage users
        2. Tag the new instances
        3. monitor and upload the new instances' data
        4. Monitor the Jira ticket progressing
        :return:
        """
        self.__run_cloud_resources()

    def run(self):
        """
        This method start the Azure CRO operations
        :return:
        """
        self.__start_cro()
