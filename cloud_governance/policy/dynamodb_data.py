
from cloud_governance.cloudtrail_upload.upload_data_cloudtrail_to_dynamodb import CloudTrailToDynamoDb
from cloud_governance.common.logger.init_logger import logger


class DynamoDbData(CloudTrailToDynamoDb):

    def __init__(self):
        super().__init__()

    def serialize_cloudtrail_data(self):
        cloud_trail_data = self.__remove_unwanted_cloudtrail_data()
        items = self._convert_datatime_to_timestamp(data=cloud_trail_data)
        serialize_data = []
        for item in items:
            serialize_data.append(self._db_operations.serialize_data_dynamodb_data(item=item))
        return serialize_data

    def __remove_unwanted_cloudtrail_data(self):
        organised_data = []
        for data in self._get_cloudtrail_data():
            if data.get('Username') not in ('cloud-governance-delete-user', 'cloud-governance-user', 'CloudabilityMonitoring', 'Cloudability') and data.get('EventName') != 'LookupEvents':
                organised_data.append(data)
        return organised_data

    def _convert_datatime_to_timestamp(self, data: list):
        """
        This method convert datetime to timestamp
        @param data:
        @return:
        """
        for item in data:
            item['EventTime'] = round(item.get('EventTime').timestamp())
        return data

    def create_table_not_exists(self):
        """
        This method create table if not exists
        @return:
        """
        try:
            self._db_client.describe_table(TableName=self._table_name)
        except self._db_client.exceptions.ResourceNotFoundException:
            self._db_operations.create_table(table_name=self._table_name, key_name='EventId')
            logger.info(f'Table is created {self._table_name}')

    def upload_data(self):
        self.create_table_not_exists()
        data = self.serialize_cloudtrail_data()
        for item in data:
            self._db_operations.put_item(table_name=self._table_name, item=item)


db = DynamoDbData()
db.upload_data()

