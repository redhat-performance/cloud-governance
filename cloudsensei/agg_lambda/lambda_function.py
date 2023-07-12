import json
import logging
import os
from datetime import datetime
from time import time

from es_operations import ESOperations
from send_email import send_email_with_ses


def lambda_handler(event, context):
    """
    This lambda function sends notifications to slack on long running resources on AWS Cloud
    :param event:
    :param context:
    :return:
    """
    start_time = time()
    logging.info(f"{lambda_handler.__name__} started at {datetime.utcnow()}")
    aws_accounts = ["perf-dept", "openshift-perfscale", "openshift-psap"]
    code = 400
    message = "Something went wrong check your es_data"
    es_operations = ESOperations()
    email_body = ""
    subject = "Cloud Report: Long running instances in the Perf&Scale AWS Accounts"
    for account in aws_accounts:
        current_date = str(datetime.utcnow().date())
        index_id = f"{account}-{current_date}"
        es_data = es_operations.get_es_data_by_id(index_id)
        if es_data:
            email_body += f"<h2>{es_data.get('_source', {}).get('subject')}</h2>"
            email_body += es_data.get('_source').get('body')
            email_body += "<hr />"
    response = send_email_with_ses(body=email_body, subject=subject, to=os.environ.get('TO_ADDRESS'), cc=os.environ.get('CC_ADDRESS'))
    if response:
        code = 200
        message = "Successfully sent an emails"
    end_time = time()
    return {
        'statusCode': code,
        'body': json.dumps(message),
        'total_running_time': f"{end_time - start_time} s"
    }
