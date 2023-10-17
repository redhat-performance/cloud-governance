import logging
from abc import ABC
from datetime import datetime, timedelta

import typeguard

from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.cost_over_usage import CostOverUsage
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.logger.init_logger import handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class AbstractCollectCROReports(ABC):
    """
    This method collects the user/instance-id data from the cost-explorer
    """

    DEFAULT_ROUND_DIGITS = 3
    ZERO = 0
    TICKET_ID_KEY = 'ticket_id'
    TICKET_ID_VALUE = 'TicketId'
    AND = 'And'
    ALLOCATED_BUDGET = 'AllocatedBudget'

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._account_name = self._environment_variables_dict.get('account', '')
        self._jira_operations = JiraOperations()
        self._public_cloud_name = self._environment_variables_dict.get('PUBLIC_CLOUD_NAME', '')
        self._es_index_cro = self._environment_variables_dict.get('CRO_ES_INDEX', '')
        self._ce_payer_index = self._environment_variables_dict.get('CE_PAYER_INDEX')
        self._es_operations = ElasticSearchOperations()

    def _get_account_budget_from_payer_ce_report(self):
        """
        This method returns the total account budget
        :return:
        :rtype:
        """
        raise NotImplementedError("Account Budget Not Implemented Error")

    @typeguard.typechecked
    @logger_time_stamp
    def _prepare_instance_data(self, instance_data: list, user: str, ticket_id: str, user_cost: float,
                              cost_estimation: float, ticket_opened_date: datetime):
        """
        This method returns es data to upload
        :param instance_data:
        :param user:
        :param ticket_id:
        :param user_cost:
        :param cost_estimation:
        :param ticket_opened_date:
        :return: dict data
        """
        instance_meta_data = []
        cluster_names = []
        for data in instance_data:
            if type(data.get('instance_data')) is not list:
                instance_meta_data.append(data.get('instance_data'))
            else:
                instance_meta_data.extend(data.get('instance_data'))
            if data.get('cluster_name'):
                cluster_names.append(data.get('cluster_name'))
        return {
            'cloud_name': self._public_cloud_name.upper(),
            'account_name': self._account_name,
            'region_name': instance_data[self.ZERO].get('region_name'),
            'user': user,
            'user_cro': instance_data[self.ZERO].get('user_cro'),
            'actual_cost': user_cost,
            'ticket_id': ticket_id,
            'ticket_id_state': 'in-progress',
            'estimated_cost': cost_estimation,
            'ticket_opened_date': ticket_opened_date.date(),
            'duration': int(instance_data[self.ZERO].get('duration')),
            'approved_manager': instance_data[self.ZERO].get('approved_manager'),
            'user_manager': instance_data[self.ZERO].get('manager'),
            'project': instance_data[self.ZERO].get('project'),
            'owner': instance_data[self.ZERO].get('owner'),
            self.ALLOCATED_BUDGET: self._get_account_budget_from_payer_ce_report(),
            'instance_data': instance_meta_data,
            'cluster_names': cluster_names,
        }

    @typeguard.typechecked
    @logger_time_stamp
    def _prepare_update_es_data(self, source: dict, instance_data: list, user_cost: float, cost_estimation: float):
        """
        This method updates the values of jira id data
        :param source:
        :param instance_data:
        :param user_cost:
        :param cost_estimation:
        :return: dict data
        """
        es_instance_data = source.get('instance_data', [])
        es_cluster_names = source.get('cluster_names', [])
        for instance in instance_data:
            instance_meta_data = instance.get('instance_data')
            if instance.get('cluster_name') and instance.get('cluster_name') not in es_cluster_names:
                source.setdefault('cluster_names', []).append(instance.get('cluster_name'))
            if type(instance_meta_data) is not list:
                instance_meta_data = [instance.get('instance_data')]
            for data in instance_meta_data:
                if data not in es_instance_data:
                    source.setdefault('instance_data', []).append(data)
        source['cluster_names'] = list(set(source.get('cluster_names', [])))
        source['duration'] = int(instance_data[self.ZERO].get('duration'))
        source['estimated_cost'] = round(cost_estimation, self.DEFAULT_ROUND_DIGITS)
        source['actual_cost'] = user_cost
        if instance_data[self.ZERO].get('user_cro') and source.get('user_cro') != instance_data[self.ZERO].get('user_cro'):
            source['user_cro'] = instance_data[self.ZERO].get('user_cro')
        if instance_data[self.ZERO].get('user') and source.get('user') != instance_data[self.ZERO].get('user'):
            source['user'] = instance_data[self.ZERO].get('user')
        source['timestamp'] = datetime.utcnow()
        if source.get('ticket_id_state') != 'in-progress':
            source['ticket_id_state'] = 'in-progress'
            source['approved_manager'] = instance_data[self.ZERO].get('approved_manager')
            source['user_manager'] = instance_data[self.ZERO].get('manager'),
            source['user_manager'] = instance_data[self.ZERO].get('manager'),
            source[self.ALLOCATED_BUDGET] = self._get_account_budget_from_payer_ce_report()
        return source

    def _check_value_in_es(self, tag_key: str, tag_value: str, ticket_id: str):
        """
        This method returns the bool on comparing the es tag_key value and tag_value
        :param tag_key:
        :param tag_value:
        :param ticket_id:
        :return:
        """
        es_data = self._es_operations.get_es_data_by_id(index=self._es_index_cro, id=ticket_id)
        es_tag_value = es_data.get('_source', {}).get(tag_key.lower(), '').lower()
        return es_tag_value == tag_value

    def _upload_cro_report_to_es(self, monitor_data: dict):
        """
        This method uploads the data to elastic search index and return the data
        :param monitor_data:
        :return:
        """
        raise NotImplementedError("Not Implemented")

    @typeguard.typechecked
    @logger_time_stamp
    def run(self, monitor_data: dict):
        """
        This method runs data collection methods
        :param monitor_data:
        :return:
        """
        result = self._upload_cro_report_to_es(monitor_data=monitor_data)
        return result
