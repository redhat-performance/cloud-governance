import json
from datetime import timedelta, datetime

import boto3


class CloudTrailOperations:
    SEARCH_SECONDS = 10

    def __init__(self, region_name: str):
        self.__cloudtrail = boto3.client('cloudtrail', region_name=region_name)
        self.__global_cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')
        self.__iam_client = boto3.client('iam')

    def __check_filter_username(self, username: str, event: dict):
        """
        This method checks for the exact username.
        @param username:
        @param event:
        @return:
        """
        if '-' in username:
            event_record = json.loads(event.get('CloudTrailEvent'))
            if event_record.get('userIdentity').get('type') == "IAMUser":
                role_arn = event_record.get('userIdentity').get('arn')
                assumerole_username, event = self.__get_username_by_role(role_arn, "CreateUser", "AWS::IAM::User")
                if assumerole_username:
                    username = assumerole_username
        return username

    def __get_cloudtrail_responses(self, start_time: datetime, end_time: datetime, resource_arn: str):
        """
        This method return all the responses from the cloudtrail for a certain time period
        @param start_time:
        @param end_time:
        @param resource_arn:
        @return:
        """
        responses = []
        if start_time:
            response = self.__global_cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': resource_arn}])
        else:
            response = self.__global_cloudtrail.lookup_events(LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': resource_arn}])
        responses.extend(response.get('Events'))
        while response.get('NextToken'):
            if start_time:
                response = self.__global_cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': resource_arn}], NextToken=response.get('NextToken'))
            else:
                response = self.__global_cloudtrail.lookup_events(LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': resource_arn}], NextToken=response.get('NextToken'))
            responses.extend(response.get('Events'))
        return responses

    def __get_role_start_time_end_time(self, role_arn: str, event_name: str):
        """
        This method get the start_time, end_time from the role/user.
        @param role_arn:
        @param event_name:
        @return:
        """
        try:
            role_name = role_arn.split('/')[-1]
            if event_name == 'CreateUser':
                start_time = self.__iam_client.get_user(UserName=role_name)['User'].get('CreateDate')
            elif event_name == 'CreateRole':
                start_time = self.__iam_client.get_role(RoleName=role_name)['Role'].get('CreateDate')
            end_time = start_time + timedelta(seconds=self.SEARCH_SECONDS)
            return [start_time, end_time]
        except:
            return ['', '']

    def __get_username_by_role(self, resource_arn: str, event_name: str, resource_type: str):
        """
        This method get the username from the role
        @param resource_arn:
        @param event_name:
        @param resource_type:
        @return:
        """
        try:
            start_time, end_time = self.__get_role_start_time_end_time(role_arn=resource_arn, event_name=event_name)
            responses = self.__get_cloudtrail_responses(start_time, end_time, resource_arn)
            for event in responses:
                if event.get('EventName') == event_name:
                    if event.get('Resources'):
                        for resource in event.get('Resources'):
                            if resource.get('ResourceType') == resource_type:
                                if resource.get('ResourceName') == resource_arn:
                                    role_username = event.get('Username')
                                    role_username = self.__check_filter_username(role_username, event)
                                    username, assumed_event = self.__check_event_is_assumed_role(event.get('CloudTrailEvent'))
                                    if username:
                                        return [username, assumed_event]
                                    return [role_username, event]
            return ['', '']
        except Exception as err:
            return ['', '']

    def __check_event_is_assumed_role(self, cloudtrail_event: str):
        """
        This method checks if it assumed_role, if it is return the username and its event from role.
        @param cloudtrail_event:
        @return:
        """
        try:
            cloudtrail_event = json.loads(cloudtrail_event)
            if cloudtrail_event.get('userIdentity').get('type') == "AssumedRole":
                role_name = cloudtrail_event.get('userIdentity').get('sessionContext').get('sessionIssuer').get('arn')
                assumerole_username, event = self.__get_username_by_role(role_name, "CreateRole", "AWS::IAM::Role")
                return [assumerole_username, event]
            return [False, '']
        except Exception as err:
            return [False, '']

    def __get_user_by_resource_id(self, start_time: datetime, end_time: datetime, resource_id: str, resource_type: str):
        """
        This method find the username of the resource_id with given resource_type
        @param start_time:
        @param end_time:
        @param resource_id:
        @param resource_type:
        @return:
        """
        try:
            response = self.__cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{
                'AttributeKey': 'ResourceType', 'AttributeValue': resource_type
            }])
            for event in response['Events']:
                if event.get('Resources'):
                    for resource in event.get('Resources'):
                        if resource.get('ResourceType') == resource_type:
                            if resource.get('ResourceName') == resource_id:
                                username, assumed_event = self.__check_event_is_assumed_role(event.get('CloudTrailEvent'))
                                if username:
                                    return [username, assumed_event]
                                return [event.get('Username'), event]
            return ['', '']
        except Exception as err:
            return ['', '']

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
        username, event = self.__get_user_by_resource_id(start_time, end_time, resource_id, resource_type)
        return self.__check_filter_username(username, event)

    def set_cloudtrail(self):
        self.__cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')

