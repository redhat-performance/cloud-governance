
from cloud_governance.aws.dynamodb_upload_data.upload_data_to_dynamodb import UploadDataToDynamoDb


class CloudTrailToDynamoDb(UploadDataToDynamoDb):
    """
    This class upload cloudtrail data to dynamodb
    """

    def __init__(self):
        super().__init__()

    def __organize_cloudtrail_data(self, cloud_trail_data: list):
        """
        This class filters the cloudtrail data
        @param cloud_trail_data:
        @return:
        """
        organised_data = []
        for data in cloud_trail_data:
            if data.get('Username') not in ('cloud-governance-delete-user', 'cloud-governance-user', 'CloudabilityMonitoring', 'Cloudability') and data.get('EventName') != 'LookupEvents':
                for resource in data.get('Resources'):
                    if resource.get('ResourceName') and not resource.get('ResourceType'):
                        data['ResourceName'] = resource.get('ResourceName')
                    data[resource.get('ResourceType')] = resource.get('ResourceName')
                organised_data.append(data)
        return organised_data

    def __get_cloudtrail_data(self):
        """
        This method extract one day cloudtrail logs
        @return:
        """
        responses = self._cloudtrail_operations.get_regional_cloudtrail_responses(StartTime=self._start_time,
                                                                                  EndTime=self._end_time)
        return responses

    def upload_data(self):
        """
        This method  creates the dynamodb table if not exists and upload the data to table
        @return:
        """
        self._create_table_not_exists(primary_key='EventId')
        cloud_trail_data = self.__get_cloudtrail_data()
        data = self.__organize_cloudtrail_data(cloud_trail_data=cloud_trail_data)
        self._upload_to_dynamo_db_table(data=data)
