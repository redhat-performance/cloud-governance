import os
import smtplib
from email.message import EmailMessage

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

    def send_email_postfix(self, subject: str, to: str, cc: list, content: str):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = "%s <%s>" % (
            'cloud-governance',
            "@".join(["cloud-governance", 'redhat.com']),
        )
        msg["To"] = "@".join([to, 'redhat.com'])
        msg["Cc"] = ",".join(cc)
        msg.add_header("Reply-To", self.reply_to)
        msg.add_header("User-Agent", self.reply_to)
        msg.set_content(content)
        email_string = msg.as_string()
        email_host = 'localhost'
        try:
            with smtplib.SMTP(email_host) as s:
                try:
                    logger.debug(email_string)
                    s.send_message(msg)
                    logger.info(f'Mail sent successfully to {to}@redhat.com')
                except smtplib.SMTPException as ex:
                    logger.info(f'Error while sending mail, {ex}')
                    return False
            return True
        except Exception as err:
            logger.info(f'Some error occurred, {err}')
            return False
