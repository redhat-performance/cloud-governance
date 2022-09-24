import os
from datetime import datetime, timedelta

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.dynamodb.dynamodb_operations import DynamoDbOperations
from cloud_governance.common.logger.init_logger import logger


class UploadDataToDynamoDb:
    """
    This class is upload cloudtrail data to DynamoDb
    """

    def __init__(self):
        self._region = os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-1')
        self._db_client = boto3.client('dynamodb', region_name=self._region)
        self._db_operations = DynamoDbOperations(region_name=self._region)
        self._table_name = os.environ.get('TABLE_NAME', 'test_data')
        self._end_time = datetime.now() - timedelta(days=0)
        self._start_time = self._end_time - timedelta(days=1)
        self._cloudtrail_operations = CloudTrailOperations(region_name=self._region)

    def __convert_datatime_to_timestamp_in_data(self, data: list):
        """
        This method convert datetime to timestamp
        @param data:
        @return:
        """
        for item in data:
            if item.get('EventTime'):
                item['EventTime'] = round(item.get('EventTime').timestamp())
        return data

    def _create_table_not_exists(self, primary_key: str):
        """
        This method create table if not exists
        @return:
        """
        try:
            self._db_client.describe_table(TableName=self._table_name)
        except self._db_client.exceptions.ResourceNotFoundException:
            self._db_operations.create_table(table_name=self._table_name, key_name=primary_key)
            logger.info(f'Table is created {self._table_name}')

    def _upload_to_dynamo_db_table(self, data: list):
        """
        This method upload data to DynamoDB
        @param data:
        @return:
        """
        data = self.__convert_datatime_to_timestamp_in_data(data)
        count = 0
        for item in data:
            self._db_operations.put_item(table_name=self._table_name, item=self._db_operations.serialize_data_dynamodb_data(item=item))
            count += 1
        return count
