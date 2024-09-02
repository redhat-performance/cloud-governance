import logging
import os
from datetime import datetime, timezone

import requests


class SlackOperations:
    """
    This class performs the Slack operations
    """

    SLACK_POST_API = 'https://slack.com/api/chat.postMessage'  # API to post messages in slack

    def __init__(self):
        self.__slack_auth_token = os.environ['SLACK_API_TOKEN']
        self.__channel_name = f'#{os.environ["SLACK_CHANNEL_NAME"]}'  # before entering channel add your app to this channel
        self.api_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.__slack_auth_token}'
        }

    def post_message(self, blocks: list, thread_ts: str = None):
        """
        This method post block message in slack
        :param thread_ts:
        :param blocks:
        :return:
        """
        json_data = {
            'channel': self.__channel_name,
            'blocks': blocks
        }
        if thread_ts:
            json_data['thread_ts'] = thread_ts
        response = requests.post(url=self.SLACK_POST_API, headers=self.api_headers, json=json_data)
        response_data = response.json()
        return response_data

    def create_thread(self, account_name: str, **kwargs):
        """
        This method sends the header first to create a thread in slack
        :return:
        """
        header = f":zap: {kwargs.get('cloud_name', '')} Daily Report @ {datetime.now(timezone.utc).date()}: Account *{account_name.title()}* has following long running instances"
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": header}}]
        response_data = self.post_message(blocks=blocks)
        if response_data:
            if response_data.get('ok'):
                logging.info(f"Successfully Created a Thread @timestamp={response_data.get('ts')}")
                return response_data.get('ts')
        return None

    def post_message_blocks_in_thread(self, message_blocks: list, thread_ts: str):
        """
        This method post messages in thread
        :param message_blocks:
        :param thread_ts:
        :return:
        """
        success_sends = 0
        for index, block in enumerate(message_blocks):
            response = self.post_message(blocks=block, thread_ts=thread_ts)
            if response.get('ok'):
                success_sends += 1
        logging.info(f"Total blocks: {len(message_blocks)}, Total Successes blocks: {success_sends}")
        return f"Total blocks: {len(message_blocks)}, Total Successes blocks: {success_sends}"
