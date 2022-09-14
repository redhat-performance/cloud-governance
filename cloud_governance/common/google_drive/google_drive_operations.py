import csv
import os.path

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from cloud_governance.common.logger.init_logger import logger


class GoogleDriveOperations:
    """
    This class perform the Google Drive Operations
    methods
    1. download_spreadsheet
    """

    def __init__(self):
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            self.__creds, _ = google.auth.default()
            self.__service = build('sheets', 'v4', credentials=self.__creds)

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
            result = self.__service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
            file_name = f'{sheet_name}.csv'
            output_file = os.path.join(file_path, file_name)
            with open(output_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerows(result.get('values'))
        except HttpError as error:
            logger.info(f'An error occurred: {error}')
        logger.info(f'Successfully downloaded {sheet_name}.csv')

    def append_values(self, spreadsheet_id, sheet_name: str, values: list, value_input_option: str = 'USER_ENTERED'):
        """
        This method append the values in the spreadsheet
        @param spreadsheet_id:
        @param sheet_name:
        @param values:
        @param value_input_option:
        @return:
        """
        try:
            body = {'values': values}
            result = self.__service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id, range=sheet_name,
                valueInputOption=value_input_option, body=body).execute()
            return result
        except HttpError as error:
            logger.info(f'An error occurred: {error}')

    def find_sheet_id_by_name(self, sheet_name: str, spreadsheet_id: str):
        """
        This method find the sheet id in the spreadsheet
        @param sheet_name:
        @param spreadsheet_id:
        @return:
        """
        sheets_with_properties = self.__service.spreadsheets() .get(spreadsheetId=spreadsheet_id, fields='sheets.properties').execute().get('sheets')
        for sheet in sheets_with_properties:
            if 'title' in sheet['properties'].keys():
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']

    def delete_rows(self, spreadsheet_id: str, sheet_name: str, row_number: int):
        """
        This method delete row from the spreadsheet bases on row number
        @param spreadsheet_id:
        @param sheet_name:
        @param row_number:
        @return:
        """
        try:
            spreadsheet_data = [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": self.find_sheet_id_by_name(sheet_name=sheet_name, spreadsheet_id=spreadsheet_id),
                            "dimension": "ROWS",
                            "startIndex": row_number,
                            "endIndex": row_number+1
                        }
                    }
                }
            ]
            update_data = {"requests": spreadsheet_data}
            updating = self.__service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=update_data)
            updating.execute()
        except HttpError as error:
            logger.into(f'An error occurred: {error}')

    def paste_csv_to_gsheet(self, csv_path, spreadsheet_id: str, sheet_name: str):
        """
        This method paste the csv data into the specific sheet
        Note: replaces the content in the rowIndex, columnIndex you specified
        @param csv_path:
        @param spreadsheet_id:
        @param sheet_name:
        @return:
        """
        csv_contents = None
        with open(csv_path, 'r') as csv_file:
            csv_contents = csv_file.read()
        if csv_contents:
            sheet_id = self.find_sheet_id_by_name(sheet_name=sheet_name, spreadsheet_id=spreadsheet_id)
            body = {
                'requests': [{
                    'pasteData': {
                        "coordinate": {
                            "sheetId": sheet_id,
                            "rowIndex": "0",
                            "columnIndex": "0",
                        },
                        "data": csv_contents,
                        "type": 'PASTE_NORMAL',
                        "delimiter": ',',
                    }
                }]
            }
            request = self.__service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            response = request.execute()
            return response
