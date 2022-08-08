import os
from datetime import datetime, timedelta

import boto3

from cloud_governance.common.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.aws.dynamodb.dynamodb_operations import DynamoDbOperations


class CloudTrailToDynamoDb:

    def __init__(self):
        self._region = os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-3')
        self._db_client = boto3.client('dynamodb', region_name=self._region)
        self._db_operations = DynamoDbOperations(region_name=self._region)
        self._table_name = os.environ.get('TABLE_NAME', 'test_data')
        self._end_time = datetime.now() - timedelta(days=0)
        self._start_time = self._end_time - timedelta(days=1)
        self._cloudtrail_operations = CloudTrailOperations(region_name=self._region)

    def _get_cloudtrail_data(self):
        """
        This method extract one day cloudtrail logs
        @return:
        """
        responses = self._cloudtrail_operations.get_regional_cloudtrail_responses(StartTime=self._start_time, EndTime=self._end_time)
        return responses



