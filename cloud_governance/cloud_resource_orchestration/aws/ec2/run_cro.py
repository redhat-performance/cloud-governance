from datetime import datetime

import boto3

from cloud_governance.cloud_resource_orchestration.aws.ec2.collect_cro_reports import CollectCROReports
from cloud_governance.cloud_resource_orchestration.aws.ec2.cost_over_usage import CostOverUsage
from cloud_governance.cloud_resource_orchestration.aws.ec2.monitor_cro_instances import MonitorCROInstances
from cloud_governance.cloud_resource_orchestration.aws.ec2.monitor_tickets import MonitorTickets
from cloud_governance.cloud_resource_orchestration.aws.ec2.tag_cro_instances import TagCROInstances
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class RunCRO:
    
    PERSISTENT_RUN_DOC_ID = f'cro_run_persistence-{datetime.utcnow().date()}'
    PERSISTENT_RUN_INDEX = 'cloud_resource_orchestration_persistence_run'
    
    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.cro_cost_over_usage = CostOverUsage()
        self.cro_reports = CollectCROReports()
        self.monitor_tickets = MonitorTickets()
        self.account = self.__environment_variables_dict.get('account', '').replace('OPENSHIFT-', '').lower().strip()
        self.__run_active_regions = self.__environment_variables_dict.get('RUN_ACTIVE_REGIONS')
        self.__region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', '')

    @logger_time_stamp
    def send_cro_alerts(self):
        """
        This method send the cost_over_usage alert and Ticket status alerts
        :return:
        """
        es_data = self.cro_cost_over_usage.es_operations.get_es_data_by_id(index=self.PERSISTENT_RUN_INDEX, id=self.PERSISTENT_RUN_DOC_ID)
        first_run = True
        if es_data:
            source = es_data.get('_source')
            last_run_time = source.get(f'last_run_{self.account.lower()}')
            if last_run_time:
                last_updated_time = datetime.strptime(last_run_time, "%Y-%m-%dT%H:%M:%S.%f").date()
                if last_updated_time == datetime.utcnow().date():
                    first_run = False
        self.__environment_variables_dict.update({'CRO_FIRST_RUN': first_run})
        if first_run:
            cost_over_usage_users = self.cro_cost_over_usage.run()
            logger.info(f'Cost Over Usage Users list: {", ".join(cost_over_usage_users)}')
            self.monitor_tickets.run()
            self.cro_reports.update_in_progress_ticket_cost()
        self.save_current_timestamp()

    @logger_time_stamp
    def save_current_timestamp(self):
        """
        This method saves the current timestamp
        Storing timestamp for not sending multiple alerts in a day, if we run any number of times
        :return:
        """
        if not self.cro_cost_over_usage.es_operations.verify_elastic_index_doc_id(index=self.PERSISTENT_RUN_INDEX, doc_id=self.PERSISTENT_RUN_DOC_ID):
            self.cro_cost_over_usage.es_operations.upload_to_elasticsearch(index=self.PERSISTENT_RUN_INDEX, data={f'last_run_{self.account}': datetime.utcnow()}, id=self.PERSISTENT_RUN_DOC_ID)
        else:
            self.cro_cost_over_usage.es_operations.update_elasticsearch_index(index=self.PERSISTENT_RUN_INDEX, metadata={f'last_run_{self.account}': datetime.utcnow()}, id=self.PERSISTENT_RUN_DOC_ID)

    @logger_time_stamp
    def run_cloud_resources(self):
        """
        This method run the aws resources in specified region or all regions
        :return:
        """
        if self.__run_active_regions:
            active_regions = [region.get('RegionName') for region in boto3.client('ec2').describe_regions()['Regions']]
            logger.info(f"""*****Running CloudResourceOrchestration in all Active regions: {active_regions}*****""")
        else:
            active_regions = [self.__region]
        for active_region in active_regions:
            cro_monitor = MonitorCROInstances(region_name=active_region)
            cro_tagging = TagCROInstances(region_name=active_region)
            self.__environment_variables_dict.update({'AWS_DEFAULT_REGION': active_region})
            logger.info(f"""Running CloudResourceOrchestration in region: {active_region}""")
            logger.info(f"""{active_region}: -> Running CRO Tagging""")
            tagging_response = cro_tagging.run()
            logger.info(f'Tagged instances : {tagging_response}')
            logger.info(f"""{active_region}: -> Running CRO Resource data Collection""")
            monitor_response = cro_monitor.run()
            if monitor_response:
                cro_reports = self.cro_reports.run(monitor_response)
                logger.info(f'Cloud Orchestration Resources: {cro_reports}')

    @logger_time_stamp
    def start_cro(self):
        """
        This method start the cro process methods
        1. Send alert to cost over usage users
        2. Tag the new instances
        3. monitor and upload the new instances' data
        4. Monitor the Jira ticket progressing
        :return:
        """
        self.send_cro_alerts()
        self.run_cloud_resources()

    @logger_time_stamp
    def run(self):
        """
        This method start the aws CRO operations
        :return:
        """
        self.start_cro()
