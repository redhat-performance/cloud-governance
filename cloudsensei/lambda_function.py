import json
import logging
import os
from time import time

import boto3
from datetime import datetime
from jinja2 import Template

from es_operations import ESOperations
from send_email import send_email_with_ses
from slack_operations import SlackOperations


class EC2Operations:
    """
    This class performs the ec2 operations
    """

    SLACK_ITEM_SIZE = 50

    def __init__(self):
        self.__ec2_client = boto3.client('ec2', region_name='us-east-1')
        self.__iam_client = boto3.client('iam')
        self.__resource_days = int(os.environ.get('RESOURCE_DAYS', 7))

    def set_ec2_client(self, region_name: str):
        """
        This method change the ec2_client object with another region
        :param region_name:
        :return:
        """
        self.__ec2_client = boto3.client('ec2', region_name=region_name)

    def __get_all_instances(self):
        """
        This method returns all instances in a region
        :return:
        """
        resource_list = []
        resources = self.__ec2_client.describe_instances()
        resource_list.extend(resources['Reservations'])
        while 'NextToken' in resources.keys():
            resources = self.__ec2_client.describe_instances(NextToken=resources['NextToken'])
            resource_list.extend(resources['Reservations'])
        return resource_list

    def get_resources(self):
        """
        This method returns all the instances running more than 7 days
        :return:
        """
        regions = self.__ec2_client.describe_regions()['Regions']
        current_datetime = datetime.utcnow().date()
        long_running_instances_by_user = {}
        for region in regions:
            region_name = region['RegionName']
            self.set_ec2_client(region_name)
            instances_list = self.__get_all_instances()
            for instances in instances_list:
                for resource in instances['Instances']:
                    skip = False
                    launch_time = resource.get('LaunchTime').date()
                    days = (current_datetime - launch_time).days
                    if days > self.__resource_days:
                        user = name = None
                        for tag in resource.get('Tags', []):
                            tag_key = tag.get('Key').lower()
                            if tag_key.lower() == 'cloudsensei':
                                skip = True
                                break
                            if tag_key == 'user':
                                user = tag.get('Value')
                            elif tag_key == 'name':
                                name = tag.get('Value')
                        if not skip and user:
                            long_running_instances_by_user.setdefault(user.lower(), {}).setdefault(region_name, []).append(
                                {'InstanceId': resource.get('InstanceId'),
                                 'Name': name, 'LaunchDate': str(launch_time),
                                 'RunningDays': f"{days} days", 'State': resource.get('State', {}).get('Name')})
        return long_running_instances_by_user

    def get_account_alias_name(self):
        """
        This method returns the account alias name
        :return:
        """
        response = self.__iam_client.list_account_aliases()
        account_alias = response['AccountAliases'][0]
        return account_alias

    def organize_message_to_send_slack(self, resources_list: dict):
        """
        This method returns the message to send to slack
        :param resources_list:
        :return:
        """

        divider = {"type": "divider"}
        keys_list = ['User', 'Region', 'Name', 'InstanceId', 'LaunchDate', 'RunningDays']
        rows = []
        for user, region_list in resources_list.items():
            for region_name, resources_list in region_list.items():
                for resources in resources_list:
                    if resources:
                        resources.update({'User': user, 'Region': region_name})
                        rows.append({
                            "type": "section",
                            "fields": [{"type": "mrkdwn", "text": f"{str(resources.get(item))}"} for item in keys_list],
                        })
            rows.append(divider)
        item_blocks = [rows[i:i + self.SLACK_ITEM_SIZE] for i in range(0, len(rows), self.SLACK_ITEM_SIZE)]  # splitting because slack block allows only 50 items
        slack_message_block = []
        for block in item_blocks:
            slack_message_block.append(block)
        return slack_message_block

    def organize_message_to_seng_mail(self, resources_list: dict):
        """
        This method returns the mail message
        :param resources_list:
        :return:
        """
        keys_list = ['User', 'Region', 'Name', 'InstanceId', 'LaunchDate', 'State',  'RunningDays']
        with open('email_template.j2') as template:
            template = Template(template.read())
            body = template.render({'resources_list': resources_list, 'keys_list': keys_list})
            return body


class ProcessData:
    def __init__(self, subject):
        self.__subject = subject

    def send_email(self, organized_ec2_data):
        """
        This method send email
        :return:
        """
        response = send_email_with_ses(body=organized_ec2_data, subject=self.__subject, to=os.environ.get('TO_ADDRESS'),
                                       cc=os.environ.get('CC_ADDRESS'))
        if response:
            return 200, "Successfully sent an emails"
        return 400, 'Something went wrong'

    def save_to_elastic_search(self, organized_ec2_data, account_name):
        """
        This method saves the data in elasticsearch
        :return:
        """
        es_operations = ESOperations()
        data = {
            'body': organized_ec2_data,
            'subject': self.__subject,
            'index_id': f"{account_name.lower()}-{str(datetime.utcnow().date())}"
        }
        if es_operations.upload_to_es(data=data, id=data.get('index_id')):
            return 200, "Successfully save date in elastic search"
        return 400, 'Something went wrong'

    def post_message_in_slack(self, slack_blocks, account_name):
        """
        This method posts message in slack
        :return:
        """
        slack_operations = SlackOperations()
        thread_ts = slack_operations.create_thread(account_name=account_name)
        code = 400
        message = 'Something went wrong, while posting to slack'
        if thread_ts:
            message = slack_operations.post_message_blocks_in_thread(message_blocks=slack_blocks, thread_ts=thread_ts)
            code = 200
        return code, message


def lambda_handler(event, context):
    """
    This lambda function sends notifications to slack on lon running resources on AWS Cloud
    :param event:
    :param context:
    :return:
    """
    start_time = time()
    logging.info(f"{lambda_handler.__name__} started at {datetime.utcnow()}")
    code = 400
    message = "Something went wrong while sending the Notification"
    extra_message = ''
    ec2_operations = EC2Operations()
    account_name = ec2_operations.get_account_alias_name()
    process_data = ProcessData(subject=f'Daily Report @{account_name} has following long running instances')
    if os.environ.get("SLACK_API_TOKEN"):
        slack_blocks = ec2_operations.organize_message_to_send_slack(ec2_operations.get_resources())
        code, message = process_data.post_message_in_slack(slack_blocks=slack_blocks, account_name=account_name)
    else:
        organized_ec2_data = ec2_operations.organize_message_to_seng_mail(ec2_operations.get_resources())
        if os.environ.get("SEND_AGG_MAIL", "no").lower() == "yes":
            code, message = process_data.save_to_elastic_search(organized_ec2_data, account_name=account_name)
            if os.environ.get('SES_HOST_ADDRESS'):
                code, message = process_data.send_email(organized_ec2_data)
        elif os.environ.get('SES_HOST_ADDRESS'):
            if os.environ.get('SES_HOST_ADDRESS'):
                code, message = process_data.send_email(organized_ec2_data)
        else:
            organized_ec2_data = ec2_operations.get_resources()
            message = organized_ec2_data
            code = 200
    end_time = time()
    return {
        'statusCode': code,
        'body': json.dumps({'message': message, 'extra_message': extra_message}),
        'total_running_time': f"{end_time - start_time} s"
    }
