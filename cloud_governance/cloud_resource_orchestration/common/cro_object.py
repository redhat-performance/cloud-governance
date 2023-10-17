import boto3

from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.aws_monitor_tickets import AWSMonitorTickets
from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.main.environment_variables import environment_variables


class CroObject:
    """
    This class implements the CRO activities
    """

    def __init__(self, public_cloud_name: str):
        self.__public_cloud_name = public_cloud_name
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__run_active_regions = self.__environment_variables_dict.get('RUN_ACTIVE_REGIONS')
        self.__region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', '')

    def cost_over_usage(self):
        """
        This method returns the cost ove rusage object
        :return:
        :rtype:
        """
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.cost_over_usage import CostOverUsage
            return CostOverUsage()
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.cost_over_usage import \
                CostOverUsage
            return CostOverUsage()

    def collect_cro_reports(self):
        """
        This method returns the cro reports collection object
        :return:
        :rtype:
        """
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.collect_cro_reports import \
                CollectCROReports
            return CollectCROReports()
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.collect_cro_reports import \
                CollectCROReports
            return CollectCROReports()

    def monitor_tickets(self):
        """
        This method returns the cro monitor tickets object
        :return:
        :rtype:
        """
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            return AWSMonitorTickets()
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.azure_monitor_tickets\
                import AzureMonitorTickets
            return AzureMonitorTickets()

    def get_tag_cro_resources_object(self, region_name: str):
        """
        This method returns the tag cro resources object
        :param region_name:
        :type region_name:
        :return:
        :rtype:
        """
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.tag_cro_instances import TagCROInstances
            return TagCROInstances(region_name=region_name)
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.tag_cro_resources import \
                TagCROResources
            return TagCROResources()

    def get_monitor_cro_resources_object(self, region_name: str):
        """
        This method returns the monitor cro resources object
        :param region_name:
        :type region_name:
        :return:
        :rtype:
        """
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.monitor_cro_instances import MonitorCROInstances
            return MonitorCROInstances(region_name=region_name)
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.monitor_cro_resources import \
                MonitorCROResources
            return MonitorCROResources()

    def get_active_regions(self):
        """
        This method returns the regions to run cro
        :return:
        :rtype:
        """
        active_regions = []
        if string_equal_ignore_case(self.__public_cloud_name, 'aws'):
            if self.__run_active_regions:
                active_regions = [region.get('RegionName') for region in
                                  boto3.client('ec2').describe_regions()['Regions']]
            else:
                active_regions = [self.__region]
        elif string_equal_ignore_case(self.__public_cloud_name, 'azure'):
            active_regions = ['all']
        return active_regions
