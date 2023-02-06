
import datetime


from cloud_governance.cloud_resource_orchestration.aws.long_run.monitor_long_run import MonitorLongRun
from cloud_governance.cloud_resource_orchestration.aws.long_run.tag_long_run import TagLongRun
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.main.environment_variables import environment_variables


class EC2LongRun:
    """
    This class tag & monitor the LongRun EC2 instances.
    User Steps:
    1. Create a Jira Issue in Clouds portal, store the JiraId
    2. Create the EC2 instance, tag JiraId
    CI Steps:
    1. CI Look the instances which are tagged with JiraId
    2. Checks the JiraId had manager approval in the data
    3. If manger approval, append LongRun tags ( Project, LongRunDays, ApprovedManager )
    """

    def __init__(self, region_name: str = ''):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__region_name = region_name if region_name else self.__environment_variables_dict.get('AWS_DEFAULT_REGION')
        self.__tag_long_run = TagLongRun(region_name=region_name)
        self.__monitor_long_run = MonitorLongRun(region_name=region_name)
        self.__ec2_operations = EC2Operations()
        self.__es_upload = ElasticUpload()
        self.__es_index = self.__environment_variables_dict.get('es_index')
        self.__account = self.__environment_variables_dict.get('account')
        self.__jira_queue = self.__environment_variables_dict.get('JIRA_QUEUE')

    def update_es_data(self, cost_estimation: float, instances: list, jira_id: str):
        """This method update the es_data"""
        es_data = self.__es_upload.elastic_search_operations.get_es_data_by_id(id=jira_id, index=self.__es_index)
        source = es_data.get('_source')
        instance_ids = source.get('instance_ids', [])
        update_es_data = {'cost_estimation': cost_estimation,
                          'long_run_days': int(instances[0].get('long_run_days')),
                          'total_instances': len(instances)}
        running_days = 0
        total_price = 0
        for instance in instances:
            running_days = max(running_days, instance.get('instance_running_days'))
            total_price += instance.get('total_run_price')
            instance_id = instance.get('instance_id')
            instance_ids.append(instance_id)
            source_instance_id = source.get(instance_id)
            update_es_data[instance_id] = \
                {'total_run_price': round(source_instance_id.get('total_run_price') + instance.get('total_run_price'),
                                         3)}
            update_es_data[instance_id].update({'total_run_hours': round(
                source_instance_id.get('total_run_hours') + instance.get('total_run_hours'), 3)})
            update_es_data[instance_id].update({'last_saved_time': instance.get('last_saved_time')})
            update_es_data[instance_id].update({'instance_state': instance.get('instance_state')})
            update_es_data[instance_id].update({'instance_running_days': instance.get('instance_running_days')})
            update_es_data[instance_id].update(
                {'ebs_cost': round(float(instance.get('ebs_cost') + source_instance_id.get('ebs_cost')), 3)})
        update_es_data['running_days'] = running_days
        update_es_data['total_run_price'] = float(source.get('total_run_price')) + total_price
        update_es_data['remaining_days'] = int(update_es_data.get('long_run_days')) - running_days
        update_es_data['timestamp'] = datetime.datetime.utcnow()
        update_es_data['instance_ids'] = list(set(instance_ids))
        self.__es_upload.elastic_search_operations.update_elasticsearch_index(index=self.__es_index, id=jira_id,
                                                                              metadata=update_es_data)
        logger.info(f'Updated the jira-id: {jira_id} data : {update_es_data}')

    def upload_new_es_data(self, jira_id: str, instances: list, cost_estimation: float):
        """This method upload the new es_data"""
        es_data = {'jira_id': jira_id, 'cloud_name': 'aws', 'account_name': self.__account,
                   'user': instances[0].get('user'), 'long_run_days': instances[0].get('long_run_days'),
                   'owner': instances[0].get('owner'), 'approved_manager': instances[0].get('approved_manager'),
                   'user_manager': instances[0].get('manager'), 'region_name': self.__region_name,
                   'project': instances[0].get('project'), 'cost_estimation': cost_estimation,
                   'jira_id_state': 'in-progress',
                   'total_instances': len(instances)}
        running_days = 0
        total_price = 0
        for instance in instances:
            running_days = max(running_days, instance.get('instance_running_days'))
            total_price += instance.get('total_run_price')
            es_data.setdefault('instance_ids', []).append(instance.get('instance_id'))
            instance.pop('user')
            instance.pop('long_run_days')
            instance.pop('owner')
            instance.pop('approved_manager')
            instance.pop('project')
            instance.pop('manager')
            es_data[instance.get('instance_id')] = instance
        es_data['running_days'] = running_days
        es_data['remaining_days'] = int(es_data.get('long_run_days')) - running_days
        es_data['total_run_price'] = round(total_price, 3)
        es_data['timestamp'] = datetime.datetime.utcnow()
        self.__es_upload.es_upload_data(items=[es_data], es_index=self.__es_index, set_index='jira_id')
        logger.info(f'Uploaded data to the es index {self.__es_index}')

    @logger_time_stamp
    def prepare_to_upload_es(self, upload_data: dict):
        """
        This method beautify and upload data to ES
        """
        for jira_id, instances in upload_data.items():
            issue_description = self.__tag_long_run.jira_operations.get_issue_description(jira_id=jira_id, state='any')
            cost_estimation = float(issue_description.get('CostEstimation', 0))
            cost_estimation += float(
                self.__tag_long_run.jira_operations.get_issue_sub_tasks_cost_estimation(jira_id=jira_id))
            if self.__jira_queue not in jira_id:
                jira_id = f"{self.__jira_queue}-{jira_id}"
            if self.__es_upload.elastic_search_operations.verify_elastic_index_doc_id(index=self.__es_index,
                                                                                      doc_id=jira_id):
                self.update_es_data(cost_estimation=cost_estimation, instances=instances, jira_id=jira_id)
            else:
                self.upload_new_es_data(cost_estimation=cost_estimation, instances=instances, jira_id=jira_id)

    def __long_run(self):
        """
        This method start the long run process
        1. tag the instances which have tag JiraId
        2. Monitor the long_run instances based on LongRunDays
        """
        tag_response = self.__tag_long_run.run()
        if tag_response:
            logger.info(f'Tags are added to the JiraId tag instances: {tag_response}')
        monitor_response = self.__monitor_long_run.run()
        if monitor_response:
            self.prepare_to_upload_es(monitor_response)

    def run(self):
        """
        This method run the long run methods
        """
        self.__long_run()
