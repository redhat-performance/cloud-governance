from datetime import datetime

from cloud_governance.cloud_resource_orchestration.common.cro_object import CroObject
from cloud_governance.cloud_resource_orchestration.utils.common_operations import string_equal_ignore_case
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class RunCRO:
    """This class monitors cro activities"""

    PERSISTENT_RUN_DOC_ID = f'cro_run_persistence-{datetime.utcnow().date()}'
    PERSISTENT_RUN_INDEX = 'cloud_resource_orchestration_persistence_run'

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_operations = ElasticSearchOperations()
        self.__account = self.__environment_variables_dict.get('account', '').lower()
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self.__cro_object = CroObject(public_cloud_name=self.__cloud_name)
        self.__cost_over_usage = self.__cro_object.cost_over_usage()
        self.__cro_reports = self.__cro_object.collect_cro_reports()
        self.__monitor_tickets = self.__cro_object.monitor_tickets()

    @logger_time_stamp
    def save_current_timestamp(self):
        """
        This method saves the current timestamp
        Storing timestamp for not sending multiple alerts in a day, if we run any number of times
        :return:
        """
        if not self.__es_operations.verify_elastic_index_doc_id(index=self.PERSISTENT_RUN_INDEX,
                                                                doc_id=self.PERSISTENT_RUN_DOC_ID):
            self.__es_operations.upload_to_elasticsearch(index=self.PERSISTENT_RUN_INDEX, data={
                f'last_run_{self.__account.lower()}': datetime.utcnow()}, id=self.PERSISTENT_RUN_DOC_ID)
        else:
            self.__es_operations.update_elasticsearch_index(index=self.PERSISTENT_RUN_INDEX,
                                                            metadata={f'last_run_{self.__account.lower()}': datetime.utcnow()},
                                                            id=self.PERSISTENT_RUN_DOC_ID)

    @logger_time_stamp
    def __send_cro_alerts(self):
        """
        This method sends the cost_over_usage alert and Ticket status alerts
        :return:
        """
        es_data = self.__es_operations.get_es_data_by_id(index=self.PERSISTENT_RUN_INDEX, id=self.PERSISTENT_RUN_DOC_ID)
        first_run = True
        try:
            if es_data:
                source = es_data.get('_source')
                last_run_time = source.get(f'last_run_{self.__account.lower()}')
                if last_run_time:
                    last_updated_time = datetime.strptime(last_run_time, "%Y-%m-%dT%H:%M:%S.%f").date()
                    if last_updated_time == datetime.utcnow().date():
                        first_run = False
            self.__environment_variables_dict.update({'CRO_FIRST_RUN': first_run})
            if first_run:
                cost_over_usage_users = self.__cost_over_usage.run()
                logger.info(f'Cost Over Usage Users list: {cost_over_usage_users}')
                self.__monitor_tickets.run()
                self.__cro_reports.update_in_progress_ticket_cost()
        except Exception as err:
            logger.error(err)
        self.save_current_timestamp()

    def __run_cloud_resources(self):
        """
        This method runs the public cloud resources and upload results to es
        :return:
        :rtype:
        """
        active_regions = self.__cro_object.get_active_regions()
        logger.info(f"""***** Running CloudResourceOrchestration in all Active regions: {active_regions} *****""")
        for active_region in active_regions:
            cro_monitor = self.__cro_object.get_monitor_cro_resources_object(region_name=active_region)
            cro_tagging = self.__cro_object.get_tag_cro_resources_object(region_name=active_region)
            if string_equal_ignore_case(self.__cloud_name, 'aws'):
                self.__environment_variables_dict.update({'AWS_DEFAULT_REGION': active_region})
            logger.info(f"""Running CloudResourceOrchestration in region: {active_region}""")
            logger.info(f"""{active_region}: -> Running CRO Tagging""")
            tagging_response = cro_tagging.run()
            logger.info(f'Tagged instances : {tagging_response}')
            logger.info(f"""{active_region}: -> Running CRO Resource data Collection""")
            monitor_response = cro_monitor.run()
            if monitor_response:
                cro_reports = self.__cro_reports.run(monitor_response)
                logger.info(f'Cloud Orchestration Resources: {cro_reports}')

    @logger_time_stamp
    def __start_cro(self):
        """
        This method starts the cro process methods
        1. Send alert to cost over usage users
        2. Tag the new instances
        3. monitor and upload the new instances' data
        4. Monitor the Jira ticket progressing
        :return:
        """
        self.__send_cro_alerts()
        self.__run_cloud_resources()

    @logger_time_stamp
    def run(self):
        """
        This method starts the aws CRO operations
        :return:
        """
        self.__start_cro()
