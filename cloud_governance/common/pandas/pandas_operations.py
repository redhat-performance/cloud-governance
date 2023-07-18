import tempfile

import pandas as pd
import typeguard

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class PandasOperations:
    """
    This class performs the pandas operations
    """
    CHUNK_SIZE = 5000

    def __init__(self, region_name: str = 'us-east-1'):
        self.__s3_operations = S3Operations(region_name=region_name)

    @typeguard.typechecked
    @logger_time_stamp
    def get_dataframe_from_csv_file(self, file_path: str):
        """
        This method returns the pandas dataframe from the csv file
        :param file_path:
        :return:
        """
        dataframes = []
        for data_chunk in pd.read_csv(filepath_or_buffer=file_path, chunksize=self.CHUNK_SIZE):
            dataframes.append(data_chunk)
        dataframe = pd.concat(dataframes, ignore_index=True)
        return dataframe

    @typeguard.typechecked
    @logger_time_stamp
    def get_dataframe_from_s3_file(self, bucket: str, key: str, download_file: str):
        """
        This method returns the pandas dataframe from the s3 file
        :return:
        """
        if not self.__s3_operations.file_exist(bucket=bucket, key=key, file_name=download_file):
            raise FileNotFoundError(f"{key}/{download_file} path is not exists else verify your credentials")
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w') as file_name:
            self.__s3_operations.download_file(bucket=bucket, key=key, download_file=download_file,
                                               file_name_path=file_name.name)
            return self.get_dataframe_from_csv_file(file_path=file_name.name)

    @typeguard.typechecked
    @logger_time_stamp
    def get_data_dictonary_from_dataframe(self, dataframe: pd.DataFrame):
        """
        This method returns the dataframe format to dictonary order
        :param dataframe:
        :return:
        """
        return dataframe.to_dict(orient='records')
