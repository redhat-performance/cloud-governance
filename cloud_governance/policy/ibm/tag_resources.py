from functools import wraps

from cloud_governance.common.clouds.ibm.classic.classic_operations import ClassicOperations
from cloud_governance.common.clouds.ibm.developer_tools.schematic_operations import SchematicOperations
from cloud_governance.common.clouds.ibm.platform_services.platform_service_operations import PlatformServiceOperations
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
        self._classic_operations = ClassicOperations()
        self.platform_operations = PlatformServiceOperations()
        self.__env_config = self.vpc_infra_operations.env_config
        self.__ibm_custom_tags_list = self.__env_config.IBM_CUSTOM_TAGS_LIST \
            if hasattr(self.__env_config, 'IBM_CUSTOM_TAGS_LIST') \
            else self.__env_config.environment_variables_dict.get('IBM_CUSTOM_TAGS_LIST')
        self.resource_to_tag = self.__env_config.RESOURCE_TO_TAG \
            if hasattr(self.__env_config, 'RESOURCE_TO_TAG') \
            else self.__env_config.environment_variables_dict.get('RESOURCE_TO_TAG')

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
    def get_schematics_workspaces_crn(self):
        """
        This method returns all schematics workspaces crn's
        :return:
        """
        return self.schematic_operations.get_all_workspaces()

    @get_resources_wrapper
    @logger_time_stamp
    def get_resource_instances_crn(self):
        """
        This method returns all resource instances crn's
        :return:
        """
        return self.platform_operations.get_resource_instances()

    @logger_time_stamp
    def get_classic_baremetals_crn(self):
        """
        This method returns all classic baremetals crn's
        :return:
        """
        hardware_ids = self._classic_operations.get_hardware_ids()
        return hardware_ids

    @logger_time_stamp
    def get_classic_virtual_machines_crn(self):
        """
        This method returns all classic baremetals crn's
        :return:
        """
        virtual_machine_ids = self._classic_operations.get_virtual_machine_ids()
        return virtual_machine_ids

    @logger_time_stamp
    def tag_all_resources(self):
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
            "resource_instances",
            "virtual_servers",
            "schematics_workspaces",
            "classic_baremetals",
            "classic_virtual_machines"
        ]
        if self.resource_to_tag and self.resource_to_tag in vpc_resources:
            vpc_resources = [self.resource_to_tag]
        logger.info(f"Running tag operation on total of {len(vpc_resources)} resources")
        errors = messages = {}
        for vpc_resource in vpc_resources:
            resources_crn = getattr(self, f'get_{vpc_resource}_crn')()
            if vpc_resource == 'classic_baremetals':
                for resource in resources_crn:
                    ok, errors_list = self._classic_operations. \
                        update_baremetal_tags(tags=tags_list, hardware_id=resource.get('id'))
                    self.process_ok_and_errors(ok, errors_list, messages, vpc_resource, errors)
            elif vpc_resource == 'classic_virtual_machines':
                for resource in resources_crn:
                    ok, errors_list = self._classic_operations. \
                        update_virtual_machine_tags(tags=tags_list, virtual_machine_id=resource.get('id'))
                    self.process_ok_and_errors(ok, errors_list, messages, vpc_resource, errors)
            else:
                logger.info(f"Started the tagging operation for {vpc_resource}")
                ok, errors_list = self.tag_operations.update_tags(resources_crn, tags=tags_list)
                self.process_ok_and_errors(ok, errors_list, messages, vpc_resource, errors)

        return {'errors': errors, 'messages': messages}

    def process_ok_and_errors(self, ok: bool, errors_list: any, messages: dict, resource: str, errors: dict):
        """
        This method processes ok and errors
        :param errors:
        :param ok:
        :param errors_list:
        :param messages:
        :param resource:
        :return:
        """
        success_message = 'tagged are added to all resources'
        if not ok:
            message = 'Unable to tag all resources'
            logger.info(f'{message}, please find the servers that are not tagged: {errors_list}')
            errors.update({resource: message, 'crns': errors_list})
        else:
            messages.update({resource: success_message})

    def run(self):
        """
        This method runs the tag operations
        :return:
        """
        return self.tag_all_resources()
