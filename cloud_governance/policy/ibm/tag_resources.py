from functools import wraps

from cloud_governance.common.clouds.ibm.developer_tools.schematic_operations import SchematicOperations
from cloud_governance.common.clouds.ibm.tagging.global_tagging_operations import GlobalTaggingOperations
from cloud_governance.common.clouds.ibm.vpc.vpc_infra_operations import VpcInfraOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


def get_resources_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        resources_crn = []
        resource_list = func(*args, **kwargs)
        for region, resources in resource_list.items():
            resources_crn.extend(
                [resource.get('crn') if isinstance(resource, dict) else resource for resource in resources])
        return list(set(resources_crn))

    return wrapper


class TagResources:
    """
    This class tags the Virtual PrivateCloud Resources
    Virtual Servers
    VPC Resources
    """

    def __init__(self):
        self.vpc_infra_operations = VpcInfraOperations()
        self.tag_operations = GlobalTaggingOperations()
        self.schematic_operations = SchematicOperations()
        self.__env_config = self.vpc_infra_operations.env_config
        self.__ibm_custom_tags_list = self.__env_config.IBM_CUSTOM_TAGS_LIST \
            if hasattr(self.__env_config, 'IBM_CUSTOM_TAGS_LIST') else None
        self.resource_to_tag = self.__env_config.RESOURCE_TO_TAG \
            if hasattr(self.__env_config, 'RESOURCE_TO_TAG') else None

    @get_resources_wrapper
    @logger_time_stamp
    def get_virtual_servers_crn(self):
        """
        This method returns all virtual server crn's
        :return:
        """
        return self.vpc_infra_operations.get_all_instances()

    @get_resources_wrapper
    @logger_time_stamp
    def get_images_crn(self):
        """
        This method returns all virtual server crn's
        :return:
        """
        return self.vpc_infra_operations.get_all_images()

    @get_resources_wrapper
    @logger_time_stamp
    def get_placement_groups_crn(self):
        """
        This method returns all placement group crn's
        :return:
        """
        return self.vpc_infra_operations.get_all_placement_groups()

    @get_resources_wrapper
    @logger_time_stamp
    def get_volumes_crn(self):
        """
        This method returns all volumes crn's
        :return:
        """
        return self.vpc_infra_operations.get_all_volumes()

    @get_resources_wrapper
    @logger_time_stamp
    def get_floating_ips_crn(self):
        """
        This method returns all floating ips crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_floating_ips()

    @get_resources_wrapper
    @logger_time_stamp
    def get_vpcs_crn(self):
        """
        This method returns all vpcs crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_vpcs()

    @get_resources_wrapper
    @logger_time_stamp
    def get_virtual_network_interfaces_crn(self):
        """
        This method returns all virtual network interfaces crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_virtual_network_interfaces()

    @get_resources_wrapper
    @logger_time_stamp
    def get_security_groups_crn(self):
        """
        This method returns all virtual security_groups crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_security_groups()

    @get_resources_wrapper
    @logger_time_stamp
    def get_public_gateways_crn(self):
        """
        This method returns all virtual public_gateways crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_public_gateways()

    @get_resources_wrapper
    @logger_time_stamp
    def get_vpc_endpoint_gateways_crn(self):
        """
        This method returns all vpc endpoint gateways crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_vpc_endpoint_gateways()

    @get_resources_wrapper
    @logger_time_stamp
    def get_schematics_workspaces_crn(self):
        """
        This method returns all schematics workspaces crn's'
        :return:
        """
        return self.schematic_operations.get_all_workspaces()

    @get_resources_wrapper
    @logger_time_stamp
    def get_load_balancers_crn(self):
        """
        This method returns all load balancers crn's'
        :return:
        """
        return self.vpc_infra_operations.get_all_load_balancers()

    @get_resources_wrapper
    @logger_time_stamp
    def get_baremetal_servers_crn(self):
        """
        This method returns all baremetals crn's
        :return:
        """
        return self.vpc_infra_operations.get_all_baremetal_servers()

    @logger_time_stamp
    def tag_all_vpc_resources(self):
        """
        This method tags all Virtual PrivateCloud Resources
        :return:
        """
        if not self.__ibm_custom_tags_list:
            return {'ok': False, 'errors': {},
                    'message': 'No tags to add resources, please export IBM_CUSTOM_TAGS_LIST in '
                               'str format. i.e "key:value, env:test"'}
        tags_list = self.__ibm_custom_tags_list.split(',')
        vpc_resources = [
            "virtual_servers",
            "placement_groups",
            "volumes",
            "floating_ips",
            "vpcs",
            "virtual_network_interfaces",
            "security_groups",
            "public_gateways",
            "vpc_endpoint_gateways",
            "load_balancers",
            "schematics_workspaces",
            "baremetal_servers",
            "images"
        ]
        if self.resource_to_tag and self.resource_to_tag in vpc_resources:
            vpc_resources = [self.resource_to_tag]
        logger.info(f"Running tag operation on total of {len(vpc_resources)} resources")
        errors = []
        messages = {}
        for vpc_resource in vpc_resources:
            message = 'tagged are added to all resources'
            resources_crn = getattr(self, f'get_{vpc_resource}_crn')()
            logger.info(f"Started the tagging operation for {vpc_resource}")
            ok, errors = self.tag_operations.update_tags(resources_crn, tags=tags_list)
            if not ok:
                message = 'Unable to tag all resources'
                logger.info(f'{message}, please find the servers that are not tagged: {errors}')
                errors.update({vpc_resource: message, 'crns': errors})
            else:
                messages.update({vpc_resource: message})

        return {'errors': errors, 'messages': messages}

    def run(self):
        """
        This method runs the tag operations
        :return:
        """
        return self.tag_all_vpc_resources()
