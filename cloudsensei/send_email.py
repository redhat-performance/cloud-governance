import logging
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP


def send_email_with_ses(to: any, body: str, subject: str, cc: any = None):
    """
    This method sends the mail
    :param subject:
    :param to:
    :param body:
    :param cc:
    :return:
    """
    host = os.environ.get("SES_HOST_ADDRESS", '')
    port = int(os.environ.get("SES_HOST_PORT", 0))
    user = os.environ.get("SES_USER_ID", )
    password = os.environ.get("SES_PASSWORD", '')
    if host and port and user and password:
        context = ssl.create_default_context()
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = "noreply@aws.rhperfscale.org"
        msg["To"] = ", ".join(to) if type(to) == list else to
        if cc:
            msg["Cc"] = ",".join(cc) if type(cc) == list else cc
        msg.attach(MIMEText(body, 'html'))
        try:
            with SMTP(host, port) as server:
                server.starttls(context=context)
                server.login(user=user, password=password)
                server.send_message(msg)
                logging.info(f"Successfully sent mail To: {to}, Cc: {cc}")
                return True
        except Exception as err:
            logging.error(f"Error raised: {err}")
    else:
        logging.info("Missing mailing fields, please check did you pass all fields")
    return False
