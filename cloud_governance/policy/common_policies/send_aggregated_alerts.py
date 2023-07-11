import json
import logging
import os
import tempfile
from datetime import date, datetime, timedelta

import typeguard
from botocore.exceptions import ClientError

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.jira.jira import logger
from cloud_governance.common.logger.init_logger import handler
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class SendAggregatedAlerts:
    """
    This class send alerts to users which conditions are not satisfied by the policies
    """

    FILE_NAME = 'resources.json'
    GLOBAL_REGION = 'us-east-1'
    TODAY_DATE = str(date.today()).replace('-', '/')

    def __init__(self):
        self.__environment_variables = environment_variables.environment_variables_dict
        self.__bucket_name = self.__environment_variables.get('BUCKET_NAME')
        self.__bucket_key = self.__environment_variables.get('BUCKET_KEY')
        self.__policies = self.__environment_variables.get('POLICIES_TO_ALERT')
        self.__s3_operations = S3Operations(region_name='us-east-2', bucket=self.__bucket_name, logs_bucket_key=self.__bucket_key)
        self.__active_regions = EC2Operations().get_active_regions()
        self.__kerberos_users = self.__get_kerberos_users_for_iam_users()
        self.__global_region_policies = ['s3-inactive', 'empty-roles']
        self.__mail_alert_days = self.__environment_variables.get('MAIL_ALERT_DAYS')
        self.__policy_action_days = self.__environment_variables.get('POLICY_ACTIONS_DAYS')
        self.__mail_message = MailMessage()
        self.__postfix = Postfix()

    @logger_time_stamp
    def __get_kerberos_users_for_iam_users(self):
        """
        This method returns the users which IAM users are not kerberos username
        :return:
        """
        responses = {}
        users = self.__environment_variables.get('KERBEROS_USERS')
        for iam_user, kerberos_user in users.items():
            responses[iam_user.lower()] = kerberos_user.lower()
        return responses

    def __get_users_agg_result(self, policy_result: list, agg_users_result: dict, policy_name: str, region: str):
        """
        This method returns the aggregated users resources list
        :param agg_users_result:
        :param policy_result:
        :return:
        """
        if policy_result:
            for response in policy_result:
                if type(response) == dict:
                    skip_policy = response.get('Skip')
                    if skip_policy in ('NA', '', None):
                        user = response.pop('User').lower()
                        response['Region'] = region
                        response['Policy'] = policy_name
                        if user in self.__kerberos_users.keys():
                            user = self.__kerberos_users.get(user)
                        agg_users_result.setdefault(user, []).append(response)

    def __get_policy_data_in_bucket(self, region: str, policy: str):
        """
        This method returns the policy data in s3 bucket
        :param region:
        :param policy:
        :return:
        """
        try:
            policy_save_path = f'{self.__bucket_key}/{region}/{policy}'
            bucket_path_file = self.__s3_operations.get_last_objects(bucket=self.__bucket_name, key_prefix=f'{policy_save_path}/{self.TODAY_DATE}')
            policy_s3_response = self.__s3_operations.get_last_s3_policy_content(s3_file_path=bucket_path_file, file_name=self.FILE_NAME)
            return json.loads(policy_s3_response) if policy_s3_response else []
        except ClientError as err:
            logger.info(err)
            return []

    @logger_time_stamp
    def __get_policy_users_list(self):
        """
        This method gets the latest policy responses
        :return:
        """
        agg_users_result = {}
        for policy in self.__policies:
            run_global_region = True if policy in self.__global_region_policies else False
            for region in self.__active_regions:
                if (region == self.GLOBAL_REGION and run_global_region) or not run_global_region:
                    self.__get_users_agg_result(policy_result=self.__get_policy_data_in_bucket(region=region, policy=policy),
                                                agg_users_result=agg_users_result, policy_name=policy, region=region)
                if region == self.GLOBAL_REGION and run_global_region:
                    break
        return agg_users_result

    def __get_policy_agg_data_by_region(self, policy_data: dict):
        """
        This method returns the policy data agg by region
        :param policy_data:
        :return:
        """
        agg_policy_region_result = {}
        for policy_name, policy_region_data in policy_data.items():
            agg_policy_region_result[policy_name] = {}
            for region_data in policy_region_data:
                region_name = region_data.get('Region').lower()
                agg_policy_region_result[policy_name].setdefault(region_name, []).append(region_data)
        return agg_policy_region_result

    @logger_time_stamp
    def __get_policy_agg_data(self, user_policy_data: list):
        """
        This method returns the data agg by policy
        :param user_policy_data:
        :return:
        """
        agg_policy_result = {}
        for result in user_policy_data:
            policy_name = result.get('Policy').lower()
            days = int(result.get('Days', 0))
            if days in self.__mail_alert_days or days in self.__policy_action_days:
                result['Action'] = 'Deleted' if days in self.__policy_action_days else 'Monitoring'
                result['DeletedDay'] = (datetime.now() + timedelta(days=self.__policy_action_days[0] - days)).date()
                agg_policy_result.setdefault(policy_name, []).append(result)
        return self.__get_policy_agg_data_by_region(policy_data=agg_policy_result)

    @logger_time_stamp
    def __send_mail_alerts_to_users(self):
        """
        This method send mail alerts to users
        :return:
        """
        policy_agg_users_list = self.__get_policy_users_list()
        for user, user_policy_data in policy_agg_users_list.items():
            handler.setLevel(logging.WARN)
            agg_policy_data = self.__get_policy_agg_data(user_policy_data=user_policy_data)
            if agg_policy_data:
                handler.setLevel(logging.INFO)
                subject, body = self.__mail_message.get_agg_policies_mail_message(user=user, user_resources=agg_policy_data)
                self.__postfix.send_email_postfix(subject=subject, content=body, to=user, cc=[], mime_type='html')

    @logger_time_stamp
    def run(self):
        """
        This method start the other methods
        :return:
        """
        self.__send_mail_alerts_to_users()
