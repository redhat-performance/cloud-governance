import os
import tempfile

import pandas as pd

from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.main.environment_variables import environment_variables


class GCPOperations:

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__gsheet_operations = GoogleDriveOperations()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID', '')

    def get_accounts_sheet(self, sheet_name: str, dir_path: str = None):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = dir_path if dir_path else tmp_dir
            file_path = f'{dir_path}/{sheet_name}.csv'
            if not os.path.exists(file_path):
                self.__gsheet_operations.download_spreadsheet(spreadsheet_id=self.__gsheet_id,
                                                              sheet_name=sheet_name,
                                                              file_path=dir_path)
            accounts_df = pd.read_csv(file_path)
            return accounts_df
