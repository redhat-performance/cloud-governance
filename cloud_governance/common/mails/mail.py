import os
import smtplib

from cloud_governance.common.logger.init_logger import logger


class Mail:
    """
    This class send mail by accepting the receivers list and body
    export sender_mail and sender_password
    create sender_password by GoogleAccount ->  Security --> Apps password
    """

    SMTP_PORT = 465

    def __init__(self):
        self.sender_mail = os.environ.get('SENDER_MAIL', '')
        self.sender_password = os.environ.get('SENDER_PASSWORD', '')

    def send_mail(self, receivers_list: list, subject: str, body):
        """
        This method sends email
        sender_password: generate from gmail apps
        @param receivers_list:
        @param subject:
        @param body:
        @return:
        """
        if self.sender_mail and self.sender_password:
            email_text = """\
From: %s
To: %s
Subject: %s

%s
""" % (self.sender_mail, ", ".join(receivers_list), subject, body)
            try:
                smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', self.SMTP_PORT)
                smtp_server.ehlo()
                smtp_server.login(self.sender_mail, self.sender_password)
                smtp_server.sendmail(self.sender_mail, receivers_list, email_text)
                smtp_server.close()
                logger.info(f"""Email sent successfully to the receivers: {receivers_list}!""")
            except Exception as err:
                logger.info(f'Something went wrong…., {err}')
        else:
            logger.info('Sender email and password is requires')
