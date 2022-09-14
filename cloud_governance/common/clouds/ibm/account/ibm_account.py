import os

import SoftLayer
import pandas as pd


from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations


class IBMAccount:

    def __init__(self):
        self.__API_USERNAME = os.environ.get('IBM_API_USERNAME', '')
        self.__API_KEY = os.environ.get('IBM_API_KEY', '')
        self.__sl_client = SoftLayer.Client(username=self.__API_USERNAME, api_key=self.__API_KEY)
        self.__account = os.environ.get('account', '')
        self.__gsheet_id = os.environ.get('GSHEET_ID', '')
        self.__gsheet_client = GoogleDriveOperations()

    def get_sl_client(self):
        """
        This method return the softlayer client
        @return:
        """
        return self.__sl_client

    def __organise_user_tags(self, tags: dict):
        """
        This method organise the tags from the gsheet
        @param tags:
        @return:
        """
        user_tags = []
        for tag, value in tags.items():
            if value.strip():
                value = value.replace('/', '-')
                user_tags.append(f'{tag.strip().lower()}:{value.strip().lower()}')
        return user_tags

    def get_user_tags_from_gsheet(self, username: str, file_path: str = '/tmp/'):
        """
        This method return the user tags from the gsheet
        @param username:
        @param file_path:
        @return:
        """
        file_name = os.path.join(file_path, f'{self.__account}.csv')
        if not os.path.exists(file_name):
            self.__gsheet_client.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name=self.__account, file_path=file_path)
        df = pd.read_csv(file_name)
        df.fillna('', inplace=True)
        df.set_index('User', inplace=True)
        tags = dict(df.loc[username])
        tags['user'] = tags.get('_Email').split('@')[0]
        for key in list(tags.keys()):
            if key.startswith('_'):
                tags.pop(key)
        return self.__organise_user_tags(tags)
