from cloud_governance.cloud_resource_orchestration.common.run_cro import RunCRO
from cloud_governance.common.jira.jira import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class CloudMonitor:
    """
    This class run CRO Monitoring
    """

    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"
    IBM = "IBM"

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', '')
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self.__monitor = self.__environment_variables_dict.get('MONITOR')
        self.__account = self.__environment_variables_dict.get('account')
        self.__run_cro = RunCRO()

    @logger_time_stamp
    def run_cloud_monitor(self):
        """
        This method run the public cloud monitor
        :return:
        :rtype:
        """
        if self.__cloud_name.upper() == self.AWS:
            logger.info(f'CLOUD_RESOURCE_ORCHESTRATION = True, PublicCloudName = {self.__cloud_name}, Account = {self.__account}')
        elif self.__cloud_name.upper() == self.AZURE:
            logger.info(f'CLOUD_RESOURCE_ORCHESTRATION = True, PublicCloudName = {self.__cloud_name}')
        self.__run_cro.run()

    def run(self):
        """
        This method monitoring the cloud resources
        """
        self.run_cloud_monitor()
