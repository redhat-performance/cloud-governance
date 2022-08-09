import csv
import os.path

import google.auth
from googleapiclient.discovery import build

from cloud_governance.common.logger.init_logger import logger


class GoogleDriveOperations:
    """
    This class perform the Google Drive Operations
    methods
    1. download_spreadsheet
    """

    def __init__(self):
        self.__creds, _ = google.auth.default()

    def download_spreadsheet(self, spreadsheet_id: str, sheet_name: str, file_path: str):
        """
        This method download spreadsheet from the Google Drive
        Used the Google Drive API
        Create GCP Project, enable Google Drive API, enable Google Spreadsheet API
        Create Service Account, and generate keys in json format
        export GOOGLE_APPLICATION_CREDENTIALS=file_location
        @return:
        """
        try:
            sheets = build('sheets', 'v4', credentials=self.__creds)
            result = sheets.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
            file_name = f'{sheet_name}.csv'
            output_file = os.path.join(file_path, file_name)
            with open(output_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerows(result.get('values'))
        except Exception as err:
            logger.info(err)
        logger.info(f'Successfully downloaded {sheet_name}.csv')
