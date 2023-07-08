import logging
from datetime import datetime, timedelta

import typeguard

from cloud_governance.cloud_resource_orchestration.aws.ec2.cost_over_usage import CostOverUsage
from cloud_governance.cloud_resource_orchestration.aws.ec2.monitor_tickets import MonitorTickets
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.jira.jira_operations import JiraOperations
from cloud_governance.common.logger.init_logger import handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class CollectCROReports:
    """
    This method collects the user/instance-id data from the cost-explorer
    """

    DEFAULT_ROUND_DIGITS = 3
    ZERO = 0
    TICKET_ID_KEY = 'ticket_id'
    COST_EXPLORER_TAGS = {TICKET_ID_KEY: 'TicketId'}
    AND = 'And'
    ALLOCATED_BUDGET = 'AllocatedBudget'

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__account_name = self.__environment_variables_dict.get('account', '').replace('OPENSHIFT-', '').strip()
        self.__cost_over_usage = CostOverUsage()
        self.jira_operations = JiraOperations()
        self.__public_cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME', '')
        self.__es_index_cro = self.__environment_variables_dict.get('CRO_ES_INDEX', '')
        self.__account_id = IAMOperations().get_aws_account_id_name()
        self.__ce_payer_index = self.__environment_variables_dict.get('CE_PAYER_INDEX')

    def get_account_budget_from_payer_ce_report(self):
        """
        This method returns the account budget from the payer ce reports
        Check policy cost_explorer_payer_billings
        :return:
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"CloudName.keyword": self.__public_cloud_name}},
                        {"term": {"AccountId.keyword": self.__account_id}},
                        {"term": {"Month": str(datetime.utcnow().year)}},
                    ]
                }
            },
            "size": 1
        }
        response = self.__cost_over_usage.es_operations.fetch_data_by_es_query(query=query, es_index=self.__ce_payer_index, search_size=1, limit_to_size=True)
        if response:
            return response[0].get('_source').get(self.ALLOCATED_BUDGET)
        return 0

    def get_total_account_usage_cost(self):
        """
        This method returns the total account budget till date for this year
        :return:
        """
        current_date = datetime.utcnow().date()
        start_date = datetime(current_date.year, 1, 1).date()
        cost_explorer_operations = self.__cost_over_usage.get_cost_explorer_operations()
        response = cost_explorer_operations.get_cost_and_usage_from_aws(start_date=str(start_date), end_date=str(current_date+timedelta(days=1)), granularity='MONTHLY')
        total_cost = cost_explorer_operations.get_filter_data(ce_data=response['ResultsByTime'], group_by=False)
        return total_cost

    @typeguard.typechecked
    @logger_time_stamp
    def get_user_cost_data(self, group_by_tag_name: str, group_by_tag_value: str, requested_date: datetime = '', forecast: bool = False, duration: int = 0, extra_filter_key_values: dict = None):
        """
        This method fetch data from the es_reports
        :param extra_filter_key_values:
        :param group_by_tag_value:
        :param group_by_tag_name:
        :param duration:
        :param forecast:
        :param requested_date:
        :return:
        """
        extra_filter_matches = [{'Tags': {'Key': group_by_tag_name, 'Values': [group_by_tag_value]}}]
        if extra_filter_key_values:
            extra_filter_matches.extend([{'Tags': {'Key': filter_key, 'Values': [filter_value]}} for filter_key, filter_value in extra_filter_key_values.items()])
        start_date = requested_date.replace(minute=self.ZERO, hour=self.ZERO, second=self.ZERO, microsecond=self.ZERO)
        if forecast:
            end_date = start_date + timedelta(days=duration)
            response = self.__cost_over_usage.get_forecast_cost_data(start_date=start_date, end_date=end_date,
                                                                     extra_matches=extra_filter_matches, extra_operation=self.AND, tag_name=group_by_tag_name)
            return_key = 'Forecast'
        else:
            response = self.__cost_over_usage.get_monthly_user_es_cost_data(start_date=start_date,
                                                                            end_date=datetime.utcnow().replace(microsecond=self.ZERO) + timedelta(days=1),
                                                                            extra_matches=extra_filter_matches, extra_operation=self.AND, tag_name=group_by_tag_name)
            return_key = 'Cost'
        if response:
            return round(response[self.ZERO].get(return_key), self.DEFAULT_ROUND_DIGITS)
        return self.ZERO

    @typeguard.typechecked
    @logger_time_stamp
    def prepare_instance_data(self, instance_data: list, user: str, ticket_id: str, user_cost: float,
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
        return {
            'cloud_name': self.__public_cloud_name.upper(),
            'account_name': self.__account_name,
            'region_name': instance_data[self.ZERO].get('region_name'),
            'user': user,
            'user_cro': instance_data[self.ZERO].get('user_cro'),
            'actual_cost': user_cost,
            'ticket_id': ticket_id,
            'ticket_id_state': 'in-progress',
            'estimated_cost': cost_estimation,
            'total_instances': len(instance_data),
            'monitored_days': (datetime.utcnow().date() - ticket_opened_date.date()).days,
            'ticket_opened_date': ticket_opened_date.date(),
            'duration': int(instance_data[self.ZERO].get('duration')),
            'approved_manager': instance_data[self.ZERO].get('approved_manager'),
            'user_manager': instance_data[self.ZERO].get('manager'),
            'project': instance_data[self.ZERO].get('project'),
            'owner': instance_data[self.ZERO].get('owner'),
            'total_spots': len([instance for instance in instance_data if instance.get('instance_plan').lower() == 'spot']),
            'total_ondemand': len([instance for instance in instance_data if instance.get('instance_plan').lower() == 'ondemand']),
            self.ALLOCATED_BUDGET: self.get_account_budget_from_payer_ce_report(),
            'instances': [f"{instance.get('instance_name')}, {instance.get('instance_id')}, "
                          f"{instance.get('instance_plan')}, "
                          f"{instance.get('instance_type')}, "
                          f"{instance.get('instance_state')}, {instance.get('instance_running_days')}" for instance in instance_data],
            'instance_types': [instance.get('instance_type') for instance in instance_data]
        }

    @typeguard.typechecked
    @logger_time_stamp
    def __prepare_update_es_data(self, source: dict, instance_data: list, user_cost: float, cost_estimation: float):
        """
        This method update the values of jira id data
        :param source:
        :param instance_data:
        :param user_cost:
        :param cost_estimation:
        :return: dict data
        """
        for instance in instance_data:
            index = [idx for idx, es_instance in enumerate(source.get('instances', [])) if instance.get('instance_id') in es_instance]
            running_days = instance.get('instance_running_days')
            if index:
                source['instances'][index[self.ZERO]] = f"{instance.get('instance_name')}, {instance.get('instance_id')}, " \
                                                f"{instance.get('instance_plan')}, {instance.get('instance_type')}, " \
                                                f"{instance.get('instance_state')}, {running_days}"
            else:
                source.setdefault('instances', []).append(f"{instance.get('instance_name')}, {instance.get('instance_id')}, "
                                                          f"{instance.get('instance_plan')}, {instance.get('instance_type')}, "
                                                          f"{instance.get('instance_state')}, {running_days}")
                source.setdefault('instance_types', []).append(instance.get('instance_type'))
                if instance.get('instance_plan', '').lower() == 'spot':
                    source['total_spots'] = source.get('total_spots', 0) + 1
                else:
                    if instance.get('instance_plan', '').lower() == 'ondemand':
                        source['total_ondemand'] = source.get('total_ondemand', 0) + 1
        MonitorTickets().verify_es_instances_state(es_data=source)
        if datetime.strptime(source.get('timestamp'), "%Y-%m-%dT%H:%M:%S.%f").date() != datetime.now().date():
            source['monitored_days'] = (datetime.utcnow().date() - source.get('ticket_opened_date')).days
        source['total_instances'] = len(source.get('instances', self.ZERO))
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
            source[self.ALLOCATED_BUDGET] = self.get_account_budget_from_payer_ce_report()
        return source

    @typeguard.typechecked
    @logger_time_stamp
    def __upload_cro_report_to_es(self, monitor_data: dict):
        """
        This method uploads the data to elastic search index and return the data
        :param monitor_data:
        :return:
        """
        upload_data = {}
        for ticket_id, instance_data in monitor_data.items():
            ticket_id = ticket_id.split('-')[-1]
            user = instance_data[self.ZERO].get('user')
            user_project = instance_data[self.ZERO].get('project')
            issue_description = self.jira_operations.get_issue_description(ticket_id=ticket_id, state='ANY')
            ticket_opened_date = issue_description.get('TicketOpenedDate')
            group_by_tag_name = self.COST_EXPLORER_TAGS[self.TICKET_ID_KEY]
            user_cost = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id,
                                                requested_date=ticket_opened_date,
                                                extra_filter_key_values={'Project': user_project})
            duration = int(instance_data[self.ZERO].get('duration', 0))
            user_forecast = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id, requested_date=datetime.utcnow(), extra_filter_key_values={'Project': user_project}, forecast=True, duration=duration)
            cost_estimation = float(instance_data[self.ZERO].get('estimated_cost', self.ZERO))
            if self.__cost_over_usage.es_operations.verify_elastic_index_doc_id(index=self.__cost_over_usage.es_index_cro, doc_id=ticket_id):
                es_data = self.__cost_over_usage.es_operations.get_es_data_by_id(id=ticket_id, index=self.__cost_over_usage.es_index_cro)
                es_data['_source']['ticket_opened_date'] = ticket_opened_date.date()
                es_data['_source']['forecast'] = user_forecast
                es_data['_source']['user'] = user
                source = self.__prepare_update_es_data(source=es_data.get('_source'), instance_data=instance_data, cost_estimation=cost_estimation, user_cost=user_cost)
                self.__cost_over_usage.es_operations.update_elasticsearch_index(index=self.__es_index_cro, id=ticket_id, metadata=source)
                upload_data[ticket_id] = source
            else:
                if ticket_id not in upload_data:
                    source = self.prepare_instance_data(instance_data=instance_data, ticket_id=ticket_id, cost_estimation=cost_estimation, user=user,  user_cost=user_cost, ticket_opened_date=ticket_opened_date)
                    source['ticket_opened_date'] = ticket_opened_date.date()
                    source['forecast'] = user_forecast
                    source['user'] = user
                    if not source.get(self.ALLOCATED_BUDGET):
                        source[self.ALLOCATED_BUDGET] = self.get_account_budget_from_payer_ce_report()
                    self.__cost_over_usage.es_operations.upload_to_elasticsearch(index=self.__es_index_cro, data=source, id=ticket_id)
                    upload_data[ticket_id] = source
        return upload_data

    @logger_time_stamp
    def update_in_progress_ticket_cost(self):
        """
        This method updates the in-progress tickets costs
        :return:
        """
        query = {"query": {"bool": {"must": [
                        {"term": {"cloud_name.keyword": self.__public_cloud_name}},
                        {"term": {"account_name.keyword": self.__account_name.upper()}},
                        {"term": {"ticket_id_state.keyword": "in-progress"}}
                    ]
                }}}
        in_progress_es_tickets = self.__cost_over_usage.es_operations.fetch_data_by_es_query(query=query, es_index=self.__es_index_cro)
        total_account_cost = self.get_total_account_usage_cost()
        for in_progress_ticket in in_progress_es_tickets:
            source_data = in_progress_ticket.get('_source')
            ticket_id = source_data.get(self.TICKET_ID_KEY)
            if source_data.get('account_name').lower() in self.__account_name.lower():
                ticket_opened_date = datetime.strptime(source_data.get('ticket_opened_date'), "%Y-%m-%d")
                duration = int(source_data.get('duration', 0))
                user_project = source_data.get('project')
                group_by_tag_name = self.COST_EXPLORER_TAGS[self.TICKET_ID_KEY]
                user_cost = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id, requested_date=ticket_opened_date)
                user_forecast = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id, requested_date=datetime.utcnow(), forecast=True, duration=duration)
                update_data = {'actual_cost': user_cost, 'forecast': user_forecast, 'timestamp': datetime.utcnow(), f'TotalCurrentUsage-{datetime.utcnow().year}': total_account_cost}
                if not source_data.get(self.ALLOCATED_BUDGET):
                    update_data[self.ALLOCATED_BUDGET] = self.get_account_budget_from_payer_ce_report()
                self.__cost_over_usage.es_operations.update_elasticsearch_index(index=self.__es_index_cro, metadata=update_data, id=ticket_id)

    @typeguard.typechecked
    @logger_time_stamp
    def run(self, monitor_data: dict):
        """
        This method runs data collection methods
        :param monitor_data:
        :return:
        """
        handler.setLevel(logging.WARN)
        result = self.__upload_cro_report_to_es(monitor_data=monitor_data)
        handler.setLevel(logging.WARN)
        return result

