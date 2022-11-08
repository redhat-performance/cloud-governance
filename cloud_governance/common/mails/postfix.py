import datetime
import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger

# https://github.com/redhat-performance/quads/blob/master/quads/tools/postman.py


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
        self.reply_to = os.environ.get('REPLY_TO', 'dev-null@redhat.com')
        self.__es_host = os.environ.get('es_host', '')
        self.__policy = os.environ.get('policy', '')
        self.__es_port = os.environ.get('es_port', '')
        self.__account = os.environ.get('account', '')
        self.__policy_output = os.environ.get('policy_output', '')
        self.bucket_name, self.key = self.get_bucketname()
        self.__es_index = 'cloud-governance-mail-messages'
        if self.__es_host:
            self.__es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        if self.__policy_output:
            self.__s3_operations = S3Operations(region_name='us-east-1')

    def get_bucketname(self):
        bucket_name = ''
        key = 'logs'
        if 's3' in self.__policy_output.lower():
            targets = self.__policy_output.split('/')
            bucket_name = targets[2]
            key = targets[3]
        else:
            bucket_name = self.__policy_output
        return bucket_name, key

    def send_email_postfix(self, subject: str, to: any, cc: list, content: str, **kwargs):
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = "%s <%s>" % (
            'cloud-governance',
            "@".join(["noreply-cloud-governance", 'redhat.com']),
        )
        if isinstance(to, str):
            msg["To"] = "@".join([to, 'redhat.com'])
        elif isinstance(to, list):
            msg["To"] = ", ".join(to)
        msg["Cc"] = ",".join(cc)
        # msg.add_header("Reply-To", self.reply_to)
        # msg.add_header("User-Agent", self.reply_to)
        if kwargs.get('filename'):
            attachment = MIMEText(open(kwargs['filename']).read())
            attachment.add_header('Content-Disposition', 'attachment',
                                  filename=kwargs['filename'].split('/')[-1])
            msg.attach(attachment)
        msg.attach(MIMEText(content))
        email_string = msg.as_string()
        email_host = 'localhost'
        try:
            with smtplib.SMTP(email_host) as s:
                try:
                    logger.debug(email_string)
                    s.send_message(msg)
                    if isinstance(to, str):
                        logger.info(f'Mail sent successfully to {to}@redhat.com')
                    elif isinstance(to, list):
                        logger.info(f'Mail sent successfully to {", ".join(to)}@redhat.com')
                    if kwargs.get('filename'):
                        file_name = kwargs['filename'].split('/')[-1]
                        date_key = datetime.datetime.now().strftime("%Y%m%d%H")
                        self.__s3_operations.upload_file(file_name_path=kwargs['filename'],
                                                         bucket=self.bucket_name, key=f'{self.key}/{self.__policy}/{date_key}',
                                                         upload_file=file_name)
                        s3_path = f'{self.__policy_output}/logs/{self.__policy}/{date_key}/{file_name}'
                        content += f'\n\nresource_file_path: s3://{s3_path}\n\n'
                    data = {'Policy': self.__policy, 'To': to, 'Cc': cc, 'Message': content, 'Account': self.__account.upper(), 'MessageType': kwargs.get('message_type')}
                    if kwargs.get('resource_id'):
                        data['resource_id'] = kwargs['resource_id']
                    if self.__es_host:
                        self.__es_operations.upload_to_elasticsearch(data=data, index=self.__es_index)
                except smtplib.SMTPException as ex:
                    logger.info(f'Error while sending mail, {ex}')
                    return False
            return True
        except Exception as err:
            logger.info(f'Some error occurred, {err}')
            return False
