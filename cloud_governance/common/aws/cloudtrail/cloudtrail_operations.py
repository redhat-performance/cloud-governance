import json
from datetime import timedelta, datetime

import boto3


class CloudTrailOperations:
    SEARCH_SECONDS = 10

    def __init__(self, region_name: str):
        self.__cloudtrail = boto3.client('cloudtrail', region_name=region_name)

    def get_username_by_instance_id_and_time(self, start_time: datetime, resource_id: str, resource_type: str):
        """
        This method find Username in cloud trail events according to start_time and resource_id
        @param start_time:
        @param resource_id:
        @param resource_type:
        @return: if user not found it return empty string
        """
        search_time = timedelta(seconds=self.SEARCH_SECONDS)
        end_time = start_time + search_time
        start_time = start_time - search_time
        try:
            response = self.__cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{
                'AttributeKey': 'ResourceType', 'AttributeValue': resource_type
            }])
            for event in response['Events']:
                if event.get('Resources'):
                    for resource in event.get('Resources'):
                        if resource.get('ResourceType') == resource_type:
                            if resource.get('ResourceName') == resource_id:
                                event_record = json.loads(event.get('CloudTrailEvent'))
                                if event_record.get('userIdentity').get('type') == "AssumedRole":
                                    return self.__get_username_from_assumed_role(start_time, end_time, event.get('Username'), "AWS::STS::AssumedRole")
                                return event.get('Username')
            return ''
        except:
            return ''

    def __get_username_from_assumed_role(self, start_time: datetime, end_time: datetime, resource_id: str, resource_type: str):
        response = self.__cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{
            'AttributeKey': 'ResourceType', 'AttributeValue': resource_type
        }])
        for event in response['Events']:
            if event.get('Resources'):
                for resource in event.get('Resources'):
                    if resource.get('ResourceType') == resource_type:
                        if resource.get('ResourceName') == resource_id:
                            return event.get('Username')

    def set_cloudtrail(self):
        self.__cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')
