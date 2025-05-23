import datetime
import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Union, Optional

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger

# https://github.com/redhat-performance/quads/blob/master/quads/tools/postman.py
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.utils.api_requests import APIRequests
from cloud_governance.main.environment_variables import environment_variables


class Postfix:
    """
    This class send mail using the postfix configuration
    install postfix and configure on machine
    $ dnf install postfix -y
    $ vi /etc/postfix/main.cf
    relayhost = [smtp.corp.redhat.com]
    inet_interfaces = all
    inet_protocols = all
    relay_domains = rdu2.scalelab.redhat.com, redhat.com
    $ systemctl restart postfix
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__LDAP_HOST_NAME = self.__environment_variables_dict.get('LDAP_HOST_NAME')
        self.__ldap_search = LdapSearch(ldap_host_name=self.__LDAP_HOST_NAME)
        self.reply_to = self.__environment_variables_dict.get('REPLY_TO', 'dev-null@redhat.com')
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__policy = self.__environment_variables_dict.get('policy', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__account = self.__environment_variables_dict.get('account', '')
        self.__policy_output = self.__environment_variables_dict.get('policy_output', '')
        self.__default_admins = self.__environment_variables_dict.get('DEFAULT_ADMINS')
        self.__email_alert = self.__environment_variables_dict.get('EMAIL_ALERT')
        self.__mail_to = self.__environment_variables_dict.get('EMAIL_TO')
        self.__mail_cc = self.__environment_variables_dict.get('EMAIL_CC')
        self.__POSTFIX_HOST = environment_variables.POSTFIX_HOST
        self.__POSTFIX_PORT = environment_variables.POSTFIX_PORT
        self.bucket_name, self.key = self.get_bucket_name()
        self.__perf_services_url = os.environ.get('PERF_SERVICES_URL')
        self.__es_index = 'cloud-governance-mail-messages'
        self.__api_request = APIRequests()
        if self.__es_host:
            self.__es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        if self.__policy_output:
            self.__s3_operations = S3Operations(region_name='us-east-1')

    def get_bucket_name(self):
        key = 'logs'
        if 's3' in self.__policy_output.lower():
            targets = self.__policy_output.split('/')
            bucket_name = targets[2]
            key = targets[3]
        else:
            bucket_name = self.__policy_output
        return bucket_name, key

    def split_emails(self, email_str: str):
        """
        This method split the mail list
        :param email_str:
        :type email_str:
        :return:
        :rtype:
        """
        splitter = "," if "," in email_str else " "
        return [item.strip() for item in email_str.split(splitter)]

    def prettify_to(self, to: Union[str, list]):
        """
        This method prettifies to
        :param to:
        :type to:
        :return:
        :rtype:
        """

        if isinstance(to, str):
            to = self.split_emails(email_str=to)
        if isinstance(to, list):
            return ','.join([item if '@redhat.com' in item else f'{item}@redhat.com' for item in to])
        return to

    def prettify_cc(self, cc: Union[str, list], to: str = ''):
        """
        This method prettifies cc
        :param to:
        :type to:
        :param cc:
        :type cc:
        :return:
        :rtype:
        """
        if isinstance(cc, str):
            cc = self.split_emails(email_str=cc)
        cc_unique_values = [cc_user if '@redhat.com' in cc_user else f'{cc_user}@redhat.com' for cc_user in cc]
        to = self.prettify_to(to=to).split(',')
        return ','.join(list(set(cc_unique_values) - set(to)))

    def __save_to_elastic(self, **kwargs):
        """
        This method uploads data to elasticsearch
        :param kwargs:
        :return:
        """
        es_data = kwargs.get('es_data')
        data = {'Policy': self.__policy,
                'Account': self.__account.upper(),
                'MessageType': kwargs.get('message_type', 'alert')}
        if es_data:
            data.update(es_data)
        if kwargs.get('resource_id'):
            data['resource_id'] = kwargs['resource_id']
        if kwargs.get('extra_purse'):
            data['extra_purse'] = round(kwargs['extra_purse'], 3)
        if kwargs.get('remaining_budget'):
            data['remaining_budget'] = kwargs['remaining_budget']
        if self.__es_host:
            self.__es_operations.upload_to_elasticsearch(data=data, index=self.__es_index)
            logger.info(f'Uploaded to es index: {self.__es_index}')
        else:
            logger.info('Error missing the es_host')

    def __save_to_s3(self, content: str, **kwargs):
        """
        This method save mail message to s3 bucket
        :return:
        """
        if kwargs.get('filename'):
            file_name = kwargs['filename'].split('/')[-1]
            date_key = datetime.datetime.now().strftime("%Y%m%d%H")
            if self.__policy_output:
                self.__s3_operations.upload_file(file_name_path=kwargs['filename'],
                                                 bucket=self.bucket_name,
                                                 key=f'{self.key}/{self.__policy}/{date_key}',
                                                 upload_file=file_name)
                s3_path = f'{self.__policy_output}/logs/{self.__policy}/{date_key}/{file_name}'
                content += f'\n\nresource_file_path: s3://{s3_path}\n\n'
                logger.info("File Saved to S3")
        self.__save_to_elastic(**kwargs)

    @logger_time_stamp
    def send_email_postfix(self, subject: str, to: any, cc: list, content: str, **kwargs):
        if self.__email_alert:
            if self.__mail_to:
                to = self.__mail_to
            if self.__mail_cc:
                cc = self.__mail_cc
            if not self.__ldap_search.get_user_details(user_name=to):
                cc.extend(self.__default_admins)
            response = {'ok': True}
            to = self.prettify_to(to)
            cc = self.prettify_cc(cc)
            kwargs.setdefault('es_data', {}).update({'To': to, 'Cc': cc, 'Message': content})
            if self.__perf_services_url:
                body = {
                    "cc": cc,
                    "to": to,
                    "subject": subject,
                    "mail_body": content,
                }
                if kwargs.get('filename'):
                    body['file_content'] = open(kwargs['filename']).read()
                    body['filename'] = kwargs['filename'].split('/')[-1]
                api_url = self.__perf_services_url + f"/postfix/send_mail"
                response = self.__api_request.post(api_url, json=body)
                response = response.json()
            else:
                msg = MIMEMultipart('alternative')
                msg["Subject"] = subject
                msg["From"] = "%s <%s>" % (
                    'cloud-governance',
                    "@".join(["noreply-cloud-governance", 'redhat.com']),
                )
                msg["To"] = to
                msg["Cc"] = cc
                # msg.add_header("Reply-To", self.reply_to)
                # msg.add_header("User-Agent", self.reply_to)
                if kwargs.get('filename'):
                    if os.path.exists(kwargs['filename']):
                        attachment = MIMEText(open(kwargs['filename']).read())
                        attachment.add_header('Content-Disposition', 'attachment',
                                              filename=kwargs['filename'].split('/')[-1])
                        msg.attach(attachment)
                if kwargs.get('mime_type'):
                    msg.attach(MIMEText(content, kwargs.get('mime_type')))
                else:
                    msg.attach(MIMEText(content))
                try:
                    with smtplib.SMTP(self.__POSTFIX_HOST, self.__POSTFIX_PORT) as s:
                        try:
                            s.send_message(msg)
                        except smtplib.SMTPException as ex:
                            logger.error(f'Error while sending mail, {ex}')
                    response = {
                        'ok': True
                    }
                except Exception as err:
                    logger.error(f'Some error occurred, {err}')
            if isinstance(response, dict) and response.get('ok'):
                logger.info(f'Mail sent successfully to {to}')
                self.__save_to_s3(content, **kwargs)
                return True
            return False
