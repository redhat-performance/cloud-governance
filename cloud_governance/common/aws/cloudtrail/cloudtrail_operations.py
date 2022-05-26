from datetime import timedelta, datetime

import boto3


class CloudTrailOperations:
    WAIT_TIME = 2

    def __init__(self, region_name: str):
        self.__cloudtrail = boto3.client('cloudtrail', region_name=region_name)

    def get_username_by_instance_id_and_time(self, start_time: datetime, resource_id: str, resource_type: str):
        """
        This method find Username in cloud trail events according to start_time and resource_id
        @param start_time:
        @param resource_id:
        @param resource_type:
        @return:
        """
        diff = timedelta(seconds=self.WAIT_TIME)
        end_time = start_time + diff
        try:
            response = self.__cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time)
            for event in response['Events']:
                if event.get('Resources'):
                    for resource in event.get('Resources'):
                        if resource.get('ResourceType') == resource_type:
                            if resource.get('ResourceName') == resource_id:
                                return event.get('Username')
            return ''
        except:
            return ''

    def set_cloudtrail(self):
        self.__cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')
