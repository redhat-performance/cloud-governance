import math
import os.path
import tempfile

import pandas as pd

from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class UploadToGsheet:
    """
    This class collects the data from clouds and uploads to the GSheet
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.gsheet_operations = GoogleDriveOperations()
        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID', '')

    def format_for_updating_the_cells(self, update_data: list, gsheet_data: pd, sheet_name: str, doc_id: str):
        """
        This method format the data to be updated to GSheet and update in the GSheet
        @param update_data:
        @param gsheet_data:
        @param sheet_name:
        @param doc_id:
        @return:
        """
        gsheet_index = gsheet_data.index
        for data in update_data:
            index = gsheet_data[doc_id] == data[0]
            cell_row = gsheet_index[index].tolist()
            if cell_row:
                row_data = gsheet_data.iloc[cell_row[0]].to_list()
                if set(row_data) != set(data):
                    cell_row = cell_row[0] + 1
                    upload_data = []
                    for value in data:
                        if isinstance(value, str):
                            upload_data.append({"userEnteredValue": {'stringValue': value}})
                        elif isinstance(value, int):
                            upload_data.append({"userEnteredValue": {'numberValue': value}})
                        else:
                            if isinstance(value, float):
                                upload_data.append({"userEnteredValue": {'numberValue': value}})
                    self.gsheet_operations.update_row_in_gsheet(data=upload_data, gsheet_id=self.__gsheet_id, row=cell_row, sheet_name=sheet_name)
            else:
                self.gsheet_operations.append_values(spreadsheet_id=self.__gsheet_id, sheet_name=sheet_name, values=[data])

    def update_cloud_agg_data(self, cloud_name: str, cloud_alias_name: str):
        """
        This method aggregate all the cloud data and updates if there is any difference
        @param cloud_alias_name:
        @param cloud_name:
        @return:
        """
        self.gsheet_operations.create_work_sheet(gsheet_id=self.__gsheet_id, sheet_name=cloud_name)
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, f'{cloud_alias_name}.csv')
            if not os.path.exists(file_path):
                self.gsheet_operations.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name=cloud_alias_name, file_path=tmp_dir)
            cloud_data = pd.read_csv(file_path)
            budget_agg = math.ceil(sum(cloud_data['Budget'].tolist()[-12:]))
            forecast_agg = sum(cloud_data['Forecast'].tolist()[-12:-1])
            actual_cost = cloud_data['ActualCost'].sum()
            available = budget_agg - actual_cost
            account_id = cloud_data['AccountId'].tolist()[0]
            account_name = cloud_data['Account'].tolist()[0]
            cost_center = cloud_data['CostCenter'].tolist()[0]
            data_upload_keys = ['AccountId', 'Account', 'CostCenter', 'Actual', 'Budget', 'Forecast', 'Available']
            data_upload_values = [int(account_id), account_name, cost_center, actual_cost, budget_agg, forecast_agg, available]
            file_path = os.path.join(tmp_dir, f'{cloud_name}.csv')
            if not os.path.exists(file_path):
                self.gsheet_operations.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name=cloud_name, file_path=tmp_dir)
            if os.path.exists(file_path):
                cloud_agg_df = pd.read_csv(file_path)
                self.format_for_updating_the_cells(update_data=[data_upload_values], gsheet_data=cloud_agg_df,
                                                   sheet_name=cloud_name, doc_id='AccountId')
            else:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv') as tmp_file:
                    tmp_file.write(f'{",".join([str(item) for item in data_upload_keys])}\n')
                    tmp_file.write(f'{",".join([str(item) for item in data_upload_values])}\n')
                    tmp_file.flush()
                    self.gsheet_operations.paste_csv_to_gsheet(csv_path=tmp_file.name, spreadsheet_id=self.__gsheet_id, sheet_name=cloud_name)

    @logger_time_stamp
    def update_data(self, cloud_data: dict):
        """
        This method update the data in the Gsheet and updates the data if there is any difference
        @return:
        """
        cloud_alias_name = cloud_data.get('cloud_alias_name').upper()
        cloud_name = cloud_data.get('cloud_name').upper()
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w') as tmp_file:
            file_path = f'/tmp/{cloud_alias_name}.csv'
            self.gsheet_operations.create_work_sheet(gsheet_id=self.__gsheet_id, sheet_name=cloud_alias_name)
            if not os.path.exists(file_path):
                self.gsheet_operations.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name=cloud_alias_name, file_path=f'/tmp')
            gsheet_row_keys = ['_id', 'AccountId', 'Account', 'Month', 'CostCenter', 'ActualCost', 'Budget', 'Forecast', 'AllocatedBudget', 'AvailableBalance']
            gsheet_row_values = []
            for data in cloud_data.get('cloud_data'):
                data_values = [data.get('index_id'), int(data.get('AccountId')), data.get('Account'), data.get('Month'), data.get('CostCenter'),
                               data.get('Actual'), data.get('Budget'), float(data.get('Forecast')),
                               int(data.get('AllocatedBudget')), data.get('Budget') - data.get('Actual')]
                gsheet_row_values.append(data_values)
            if os.path.exists(file_path):
                data_in_gsheet = pd.read_csv(file_path)
                self.format_for_updating_the_cells(update_data=gsheet_row_values, gsheet_data=data_in_gsheet, sheet_name=cloud_alias_name, doc_id='_id')
                os.remove(file_path)
            else:
                total_data = [gsheet_row_keys]
                total_data.extend(gsheet_row_values)
                for data in total_data:
                    tmp_file.write(f'{",".join((str(item) for item in data))}\n')
                tmp_file.flush()
                self.gsheet_operations.paste_csv_to_gsheet(csv_path=tmp_file.name, spreadsheet_id=self.__gsheet_id, sheet_name=cloud_alias_name)
        self.update_cloud_agg_data(cloud_name=cloud_name, cloud_alias_name=cloud_alias_name)
