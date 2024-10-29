from ibm_platform_services.global_tagging_v1 import GlobalTaggingV1, Resource

from cloud_governance.common.clouds.ibm.account.ibm_authenticator import IBMAuthenticator
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class GlobalTaggingOperations(IBMAuthenticator):
    """
    This class performs tagging operations on cloud resources.
    """
    BATCH_SIZE = 100

    def __init__(self):
        super().__init__()
        self.__tag_service = GlobalTaggingV1(authenticator=self.iam_authenticator)

    @logger_time_stamp
    def update_tags(self, resources_crn: list, tags: list):
        """
        This method updates the tags associated with an instance.
        :param resources_crn:
        :param tags:
        :return:
        """
        resources_list = [Resource(resource_crn) for resource_crn in resources_crn]
        resources_batch_list = [resources_list[i:i + self.BATCH_SIZE]
                                for i in range(0, len(resources_list), self.BATCH_SIZE)]
        success = 0
        errors = []
        for resource_batch in resources_batch_list:
            responses = self.__tag_service.attach_tag(resources=resource_batch, tag_names=tags) \
                .get_result()['results']
            for resource in responses:
                if resource['is_error']:
                    errors.append(resource.get('resource_id'))
                    logger.error(f'Unable to attach resource tags to: {resource["resource_id"]}')
                else:
                    success += 1
        return success == len(resources_crn), errors
