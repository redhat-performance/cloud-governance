from datetime import datetime, timedelta, timezone

import pandas
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.common.utils.utils import Utils
from cloud_governance.main.environment_variables import environment_variables


class SendAggregatedAlerts:
    """
    This class send alerts to users which conditions are not satisfied by the policies
    """

    def __init__(self):
        self.__environment_variables = environment_variables.environment_variables_dict
        self.__days_to_delete_resource = int(self.__environment_variables.get('DAYS_TO_DELETE_RESOURCE'))
        self.__mail_to = self.__environment_variables.get('EMAIL_TO')  # testing purposes
        self.__mail_cc = self.__environment_variables.get('EMAIL_CC', [])
        self.__alert_dry_run = self.__environment_variables.get('ALERT_DRY_RUN')
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()
        self.__es_operations = ElasticSearchOperations()

    def __get_es_data(self):
        """
        This method returns the current day policy data from the elastic_search database
        :return:
        :rtype:
        """
        current_date = (datetime.now(timezone.utc).date()).__str__()
        policy_es_index = self.__environment_variables.get('es_index')
        account_name = (self.__environment_variables.get('account', '').upper()
                        .replace('OPENSHIFT-', '')
                        .replace('OPENSHIFT', '').strip())
        query = {
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "account.keyword": {
                                    "value": account_name
                                }
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "terms": {
                                "policy.keyword": [
                                    "ebs_in_use",
                                    "instance_run", "cluster_run", "optimize_resource_report",
                                    "optimize_resources_report", "skipped_resources"
                                ]
                            }
                        }
                    ],
                    "filter": [
                        {
                            "range": {
                                "timestamp": {
                                    "format": "yyyy-MM-dd",
                                    "lte": current_date,
                                    "gte": current_date
                                }
                            }
                        }
                    ]
                }
            }
        }
        records = self.__es_operations.post_query(query=query, es_index=policy_es_index)
        return [record.get('_source') for record in records]

    def __remove_duplicates(self, policy_es_data: list):
        """
        This method removes the duplicate  data
        :return:
        :rtype:
        """
        if policy_es_data:
            df = pandas.DataFrame(policy_es_data)
            df.sort_values(inplace=True, by=['policy'])
            df.fillna(value='', inplace=True)
            df.drop_duplicates(subset='ResourceId', inplace=True)
            return df.to_dict(orient="records")
        return policy_es_data

    def __group_by_policy(self, policy_data: list):
        """
        This method returns the data grouped by policy
        :param policy_data:
        :type policy_data:
        :return:
        :rtype:
        """
        policy_group_data = {}
        for record in policy_data:
            policy_group_data.setdefault(record.get('policy', 'NA'), []).append(record)
        policy_data_list = []
        for _, values in policy_group_data.items():
            policy_data_list.extend(values)
        return policy_data_list

    def __group_by_user(self, policy_data: list):
        """
        This method returns the data grouped by user files
        :param policy_data:
        :type policy_data:
        :return:
        :rtype:
        """
        user_data = {}
        for record in policy_data:
            user_data.setdefault(record.get('User', 'NA'), []).append(record)
        return user_data

    def __update_delete_days(self, policy_es_data: list):
        """
        This method returns the resource delete date
        :param policy_es_data:
        :type policy_es_data:
        :return:
        :rtype:
        """
        filtered_policy_es_data = []
        for record in policy_es_data:
            try:
                days = record.get('ClusterResourcesCount')
                if not days:
                    days = record.get('CleanUpDays')
                if not days:
                    days = record.get('Days')
                if not days:
                    days = record.get('StoppedDays')
                if days:
                    days = int(days)
                if not days:
                    days = 0
                alert_user = True if self.__alert_dry_run else False
                dry_run = record.get('DryRun')
                if record.get('ExpireDays'):
                    days_to_take_action = int(record.get('ExpireDays'))
                else:
                    days_to_take_action = int(self.__days_to_delete_resource)
                if not record.get('SkipPolicy'):
                    record['SkipPolicy'] = 'NA'
                delete_date = ''
                if record.get('SkipPolicy') != 'NA':
                    delete_date = 'skip_delete'
                if days_to_take_action - 5 == days:
                    delete_date = (datetime.utcnow() + timedelta(days=5)).date()
                    alert_user = True
                elif days == days_to_take_action - 3:
                    delete_date = (datetime.utcnow() + timedelta(days=3)).date()
                    alert_user = True
                else:
                    if days >= days_to_take_action:
                        delete_date = datetime.utcnow().date().__str__()
                        alert_user = True
                if record.get('policy') in ['empty_roles', 's3_inactive']:
                    record['RegionName'] = 'us-east-1'
                if Utils.equal_ignore_case(dry_run, 'yes'):
                    record['DeleteDate'] = 'dry_run=yes'
                    filtered_policy_es_data.append(record)
                else:
                    if alert_user:
                        if delete_date != '' and delete_date != 'skip_delete' and Utils.equal_ignore_case(dry_run, 'no'):
                            record['DeleteDate'] = delete_date.__str__()
                            filtered_policy_es_data.append(record)

            except Exception as err:
                raise err
        return filtered_policy_es_data

    def __send_aggregate_email_by_es_data(self):
        """
        This method sends an alert using the elasticsearch data
        :return:
        :rtype:
        """
        policy_es_data = self.__get_es_data()
        policy_es_data = self.__remove_duplicates(policy_es_data=policy_es_data)
        policy_es_data = self.__update_delete_days(policy_es_data)
        if self.__environment_variables.get('ADMIN_MAIL_LIST', ''):
            to_mail_list = self.__environment_variables.get('ADMIN_MAIL_LIST', '')
            group_by_policy = self.__group_by_policy(policy_data=policy_es_data)
            if group_by_policy:
                subject, body = self.__mail_message.get_policy_alert_message(policy_data=group_by_policy)
                self.__postfix.send_email_postfix(subject=subject, content=body, to=to_mail_list, cc=[], mime_type='html')
        else:
            user_policy_data = self.__group_by_user(policy_data=policy_es_data)
            for user, user_records in user_policy_data.items():
                if user_records:
                    subject, body = self.__mail_message.get_policy_alert_message(policy_data=user_records, user=user)
                    self.__postfix.send_email_postfix(subject=subject, content=body, to=user, cc=[],
                                                      mime_type='html')

    @logger_time_stamp
    def run(self):
        """
        This method start the other methods
        :return:
        """
        self.__send_aggregate_email_by_es_data()
