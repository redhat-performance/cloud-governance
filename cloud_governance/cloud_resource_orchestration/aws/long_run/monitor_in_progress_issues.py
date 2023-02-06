from datetime import datetime

from cloud_governance.cloud_resource_orchestration.common.ec2_monitor_operations import EC2MonitorOperations
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.main.environment_variables import environment_variables


class MonitorInProgressIssues:
    """
    This class monitor the in-progress jira instances
    If the instances are terminated then it closes the JiraTicket
    """

    def __init__(self, region_name: str = ''):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.__ec2_operations = EC2Operations(region=self.__region_name)
        self.jira_operations = JiraOperations()
        self.__es_upload = ElasticUpload()
        self.__es_index = self.__environment_variables_dict.get('es_index')
        self.__ec2_monitor_operations = EC2MonitorOperations(region_name=self.__region_name)
        self.__jira_queue = self.__environment_variables_dict.get('JIRA_QUEUE')

    def __update_data_and_close_ticket(self, jira_id: str):
        """
        This method update data in the es and close the ticket
        """
        update_data = {'jira_id_state': 'Closed', 'instance_state': 'terminated', 'timestamp': datetime.utcnow()}
        self.__es_upload.elastic_search_operations.update_elasticsearch_index(index=self.__es_index, metadata=update_data, id=jira_id)
        self.jira_operations.move_issue_state(jira_id=jira_id, state='closed')

    def monitor_progress_issues(self):
        """
        This method monitor the in-progress issues, and closed the issue if the instance is terminated
        """
        jira_ids = self.jira_operations.get_all_issues_in_progress()
        es_jira_ids = []
        for jira_id in jira_ids:
            if self.__es_upload.elastic_search_operations.verify_elastic_index_doc_id(index=self.__es_index, doc_id=jira_id):
                es_jira_ids.append(jira_id)
        long_run_jira_ids = []
        long_run_instances = self.__ec2_monitor_operations.get_instances_by_filtering(tag_key_name='JiraId')
        for instance in long_run_instances:
            for resource in instance['Instances']:
                jira_id = self.__ec2_operations.get_tag_value_from_tags(tags=resource.get('Tags'), tag_name='JiraId')
                if self.__jira_queue not in jira_id:
                    jira_id = f'{self.__jira_queue}-{jira_id}'
                long_run_jira_ids.append(jira_id)
        terminated_jira_ids = set(es_jira_ids) - set(long_run_jira_ids)
        for jira_id in terminated_jira_ids:
            es_data = self.__es_upload.elastic_search_operations.get_es_data_by_id(id=jira_id, index=self.__es_index)
            source = es_data.get('_source')
            instance_ids = source.get('instance_ids')
            total_price = 0
            terminated = 0
            for instance_id in instance_ids:
                if instance_id.get('instance_state') != 'terminated':
                    last_saved_time = instance_id.get('last_saved_time')
                    trails = self.__ec2_monitor_operations.get_instance_logs(instance_id, last_saved_time=last_saved_time)
                    run_hours = self.__ec2_monitor_operations.get_run_hours_from_trails(last_saved_time=last_saved_time, trails=trails,
                                                                                        launch_time=instance_id.get('instance_create_time'),
                                                                                        last_instance_state=instance_id.get('instance_state'))
                    price = self.__ec2_monitor_operations.get_instance_hours_price(instance_type=instance_id.get('instance_type'), run_hours=run_hours)
                    source[instance_id]['total_run_price'] = round(float(source[instance_id]['total_run_price']) + price, 3)
                    source[instance_id]['total_run_hours'] = round(run_hours + float(source[instance_id]['total_run_hours']), 3)
                    source[instance_id]['instance_state'] = 'terminated'
                    total_price += price
                    terminated += 1
            source['total_run_price'] = total_price
            source['timestamp'] = datetime.utcnow()
            if source.get('remaining_days') == source.get('long_run_days') or terminated == len(instance_ids):
                self.__update_data_and_close_ticket(jira_id=jira_id)
        return terminated_jira_ids
