import logging
from datetime import datetime, timedelta

import typeguard

from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.cost_over_usage import CostOverUsage
from cloud_governance.cloud_resource_orchestration.clouds.common.abstract_collect_cro_reports import \
    AbstractCollectCROReports
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class CollectCROReports(AbstractCollectCROReports):
    """
    This method collects the user/instance-id data from the cost-explorer
    """

    def __init__(self):
        super().__init__()
        self.__cost_over_usage = CostOverUsage()
        self._account_id = self._environment_variables_dict.get('AZURE_SUBSCRIPTION_ID')
        self.__scope = f'subscriptions/{self._account_id}'

    def _get_account_budget_from_payer_ce_report(self):
        """
        This method returns the account budget from the payer ce reports
        Check policy cost_explorer_payer_billings
        :return:
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"CloudName.keyword": self._public_cloud_name}},
                        {"term": {"AccountId.keyword": self._account_id}},
                        {"term": {"Month": str(datetime.utcnow().year)}},
                    ]
                }
            },
            "size": 1
        }
        response = self._es_operations.fetch_data_by_es_query(query=query, es_index=self._ce_payer_index, search_size=1,
                                                              limit_to_size=True)
        if response:
            return response[0].get('_source').get(self.ALLOCATED_BUDGET)
        return 0

    @typeguard.typechecked
    @logger_time_stamp
    def get_user_cost_data(self, group_by_tag_name: str, group_by_tag_value: str, requested_date: datetime = '', forecast: bool = False, duration: int = 0, extra_filter_key_values: dict = None):
        """
        This method fetches data from the es_reports
        :param extra_filter_key_values:
        :param group_by_tag_value:
        :param group_by_tag_name:
        :param duration:
        :param forecast:
        :param requested_date:
        :return:
        """
        extra_filter_matches = [{'Tags': {'Key': group_by_tag_name, 'Values': [group_by_tag_value]}}]
        tags = {group_by_tag_name: group_by_tag_value}
        if extra_filter_key_values:
            tags.update({{filter_key: filter_value} for filter_key, filter_value in extra_filter_key_values.items()})
        start_date = requested_date.replace(minute=self.ZERO, hour=self.ZERO, second=self.ZERO, microsecond=self.ZERO)
        response = {}
        if forecast:
            # Todo Will Add in future release
            resource_type = 'Forecast'
            pass
        else:
            end_date = datetime.utcnow().replace(microsecond=self.ZERO) + timedelta(days=1)
            response = self.__cost_over_usage.get_monthly_user_es_cost_data(start_date=start_date, end_date=end_date,
                                                                            extra_matches=extra_filter_matches,
                                                                            extra_operation=self.AND,
                                                                            tag_name=group_by_tag_name, tags=tags)
            resource_type = 'Cost'
        if response:
            return round(response[self.ZERO].get(resource_type), self.DEFAULT_ROUND_DIGITS)
        return self.ZERO

    @typeguard.typechecked
    def _upload_cro_report_to_es(self, monitor_data: dict):
        """
        This method uploads the data to elastic search index and return the data
        :param monitor_data:
        :return:
        """
        upload_data = {}
        for ticket_id, instance_data in monitor_data.items():
            if instance_data:
                ticket_id = ticket_id.split('-')[-1]
                user = instance_data[self.ZERO].get('user')
                issue_description = self._jira_operations.get_issue_description(ticket_id=ticket_id, state='ANY')
                ticket_opened_date = issue_description.get('TicketOpenedDate')
                group_by_tag_name = self.TICKET_ID_VALUE
                user_cost = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id,
                                                    requested_date=ticket_opened_date)
                cost_estimation = float(instance_data[self.ZERO].get('estimated_cost', self.ZERO))
                if self._es_operations.verify_elastic_index_doc_id(index=self.__cost_over_usage.es_index_cro,
                                                                   doc_id=ticket_id):
                    if self._check_value_in_es(tag_key='ticket_id_state', tag_value='in-progress', ticket_id=ticket_id):
                        es_data = self._es_operations.get_es_data_by_id(id=ticket_id, index=self.__cost_over_usage.es_index_cro)
                        es_data['_source']['ticket_opened_date'] = ticket_opened_date.date()
                        es_data['_source']['user'] = user
                        source = self._prepare_update_es_data(source=es_data.get('_source'), instance_data=instance_data, cost_estimation=cost_estimation, user_cost=user_cost)
                        self._es_operations.update_elasticsearch_index(index=self._es_index_cro, id=ticket_id, metadata=source)
                        upload_data[ticket_id] = source
                else:
                    if ticket_id not in upload_data:
                        source = self._prepare_instance_data(instance_data=instance_data, ticket_id=ticket_id,
                                                             cost_estimation=cost_estimation, user=user,
                                                             user_cost=user_cost, ticket_opened_date=ticket_opened_date)
                        source['ticket_opened_date'] = ticket_opened_date.date()
                        source['user'] = user
                        if not source.get(self.ALLOCATED_BUDGET):
                            source[self.ALLOCATED_BUDGET] = self._get_account_budget_from_payer_ce_report()
                        self.__cost_over_usage.es_operations.upload_to_elasticsearch(index=self._es_index_cro, data=source, id=ticket_id)
                        upload_data[ticket_id] = source
        return upload_data

    def _get_total_account_usage_cost(self):
        """
        This method returns the total account budget till date for this year
        :return:
        """
        current_date = datetime.utcnow()
        start_date = datetime(current_date.year, 1, 1, 0, 0, 0)
        end_date = current_date + timedelta(days=1)
        cost_explorer_operations = self.__cost_over_usage.get_cost_management_object()
        response = cost_explorer_operations.get_usage(scope=self.__scope, start_date=start_date, end_date=end_date,
                                                      granularity='Monthly')
        total_cost = cost_explorer_operations.get_total_cost(cost_data=response)
        return total_cost

    @logger_time_stamp
    def update_in_progress_ticket_cost(self):
        """
        This method updates the in-progress tickets costs
        :return:
        """
        query = {"query": {"bool": {"must": [
            {"term": {"cloud_name.keyword": self._public_cloud_name}},
            {"term": {"account_name.keyword": self._account_name.upper()}},
            {"term": {"ticket_id_state.keyword": "in-progress"}}
        ]
        }}}
        in_progress_es_tickets = self._es_operations.fetch_data_by_es_query(query=query, es_index=self._es_index_cro)
        total_account_cost = self._get_total_account_usage_cost()
        for in_progress_ticket in in_progress_es_tickets:
            source_data = in_progress_ticket.get('_source')
            ticket_id = source_data.get(self.TICKET_ID_KEY)
            if source_data.get('account_name').lower() in self._account_name.lower():
                ticket_opened_date = datetime.strptime(source_data.get('ticket_opened_date'), "%Y-%m-%d")
                group_by_tag_name = self.TICKET_ID_VALUE
                user_cost = self.get_user_cost_data(group_by_tag_name=group_by_tag_name, group_by_tag_value=ticket_id,
                                                    requested_date=ticket_opened_date)
                user_daily_cost = eval(source_data.get('user_daily_cost', "{}"))
                user_name = source_data.get('user')
                if not user_name:
                    user_name = source_data.get('user_cro')
                ce_user_daily_report = self.__get_user_daily_usage_report(days=4, group_by_tag_value=ticket_id,
                                                                          group_by_tag_name=group_by_tag_name,
                                                                          user_name=user_name)
                user_daily_cost.update(ce_user_daily_report)
                update_data = {'actual_cost': user_cost, 'timestamp': datetime.utcnow(),
                               f'TotalCurrentUsage-{datetime.utcnow().year}': total_account_cost,
                               'user_daily_cost': str(user_daily_cost)}
                if not source_data.get(self.ALLOCATED_BUDGET):
                    update_data[self.ALLOCATED_BUDGET] = self._get_account_budget_from_payer_ce_report()
                self._es_operations.update_elasticsearch_index(index=self._es_index_cro, metadata=update_data, id=ticket_id)

    def __get_user_daily_usage_report(self, days: int, group_by_tag_name: str, group_by_tag_value: str, user_name: str):
        """
        This method returns the users daily report from last X days
        :param days:
        :return:
        """
        user_daily_usage_report = {}
        self._get_user_usage_by_granularity(tag_name=group_by_tag_name, tag_value=group_by_tag_value,
                                            days=days, result_back_data=user_daily_usage_report)
        self._get_user_usage_by_granularity(tag_name='User', tag_value=user_name,
                                            days=days, result_back_data=user_daily_usage_report)
        return user_daily_usage_report

    def _get_user_usage_by_granularity(self, result_back_data: dict, tag_name: str, days: int, tag_value):
        """
        This method returns the organized input of the usage_reports
        :param result_back_data:
        :param tag_name:
        :param days:
        :param tag_value:
        :return:
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        cost_explorer_object = self.__cost_over_usage.get_cost_management_object()
        ce_daily_usage = cost_explorer_object.get_usage(scope=self.__scope, grouping=[tag_name], granularity='Daily',
                                                        start_date=start_date,
                                                        end_date=end_date, tags={tag_name: tag_value})
        filtered_ce_daily_usage = cost_explorer_object.get_prettify_data(cost_data=ce_daily_usage)
        for daily_cost in filtered_ce_daily_usage:
            start_date = daily_cost.get('UsageDate')
            if start_date:
                start_date = str(start_date)
                start_date = f'{start_date[0:4]}-{start_date[4:6]}-{start_date[6:]}'
            usage = round(float(daily_cost.get('Cost')), self.DEFAULT_ROUND_DIGITS)
            result_back_data.setdefault(start_date, {}).update({daily_cost.get('TagValue'): usage})
