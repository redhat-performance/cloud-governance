import json
import os
import time
from datetime import timedelta, datetime

import boto3

from cloud_governance.common.logger.init_logger import logger


class CloudTrailOperations:
    SEARCH_SECONDS = 10
    SLEEP_SECONDS = 120
    LOOKBACK_DAYS = 30

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

    def __ger_username_from_arn(self, resource_arn: str):
        """
        This method return the username from the userIdentity arn
        """
        events = self.__get_cloudtrail_responses(resource_arn=resource_arn, start_time=None, end_time=None)
        for event in events:
            for resource in event.get('Resources'):
                if resource.get('ResourceType') == 'AWS::STS::AssumedRole':
                    if resource.get('ResourceName') == resource_arn:
                        username, assumed_event = self.__check_event_is_assumed_role(event.get('CloudTrailEvent'))
                        if username:
                            return [username, assumed_event]
                        return [event.get('Username'), event]
        return ['', '']

    def __extract_username_from_arn(self, arn: str, user_type: str):
        """
        Extract username from ARN based on userIdentity type.
        @param arn: The ARN from userIdentity
        @param user_type: The userIdentity type (IAMUser, AssumedRole, FederatedUser, etc.)
        @return: username or empty string
        """
        if not arn or '/' not in arn:
            return ''

        # ARN formats:
        # IAMUser: arn:aws:iam::account:user/[path/]username
        # AssumedRole: arn:aws:sts::account:assumed-role/role-name/session-name
        # FederatedUser: arn:aws:sts::account:federated-user/username
        # Root: arn:aws:iam::account:root (no slash, return 'root')

        parts = arn.split('/')
        if len(parts) < 2:
            # No username in ARN (e.g., root user)
            return parts[-1] if parts else ''

        # Last part is always the username/session-name
        return parts[-1]

    def __check_event_is_assumed_role(self, cloudtrail_event_str: str):
        """
        This method extracts username from userIdentity ARN for IAM users and AssumedRole users.
        For SAML SSO (AssumedRole), it extracts the username from the session name in the ARN.
        For IAM users, it extracts the username from the ARN path.
        @param cloudtrail_event_str: JSON string of CloudTrailEvent
        @return: [username, parsed_event] or [False, '']
        """
        try:
            cloudtrail_event = json.loads(cloudtrail_event_str)
            user_identity = cloudtrail_event.get('userIdentity', {})
            user_type = user_identity.get('type')
            arn = user_identity.get('arn')

            # Handle supported user types by extracting from ARN
            if user_type in ('AssumedRole', 'IAMUser', 'FederatedUser'):
                username = self.__extract_username_from_arn(arn, user_type)
                if username:
                    # Return parsed event wrapped in a dict with CloudTrailEvent key for consistency
                    return [username, {'CloudTrailEvent': cloudtrail_event_str}]

            # For Root or other types without proper ARN
            if user_type == 'Root':
                return ['root', {'CloudTrailEvent': cloudtrail_event_str}]

            return [False, '']
        except Exception as err:
            return [False, '']

    def get_full_responses(self, **kwargs):
        """
        This method return all responses
        @param kwargs:
        @return:
        """
        responses = []
        response = self.__cloudtrail.lookup_events(**kwargs)
        responses.extend(response['Events'])
        while response.get('NextToken'):
            response = self.__cloudtrail.lookup_events(**kwargs, NextToken=response.get('NextToken'))
            responses.extend(response['Events'])
        if responses:
            return responses
        return []

    def __get_user_by_resource_id(self, start_time: datetime, end_time: datetime, resource_id: str, resource_type: str, event_type: str):
        """
        This method find the username of the resource_id with given resource_type
        @param start_time:
        @param end_time:
        @param resource_id:
        @param resource_type:
        @return:
        """
        try:
            responses = self.get_full_responses(StartTime=start_time, EndTime=end_time, LookupAttributes=[{
                'AttributeKey': event_type, 'AttributeValue': resource_type}])
            for event in responses:
                if event.get('EventName') == resource_type:
                    if event.get('Resources'):
                        for resource in event.get('Resources'):
                            if resource.get('ResourceName') == resource_id:
                                username, assumed_event = self.__check_event_is_assumed_role(event.get('CloudTrailEvent'))
                                if username:
                                    return [username, assumed_event]
                                return [event.get('Username'), event]
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

    def __get_time_difference(self, start_time: datetime):
        """
        This method returns seconds in difference of current time and start time
        @param start_time:
        @return:
        """
        current_time = datetime.now(start_time.tzinfo).replace(tzinfo=None)
        diff = (current_time - start_time.replace(tzinfo=None))
        return (diff.days * 24 * 60 * 60) + diff.seconds

    def get_username_by_instance_id_and_time(self, resource_id: str, resource_type: str, start_time: datetime = '', event_type: str = 'ResourceType', end_time: datetime = None):
        """
        This method find Username in cloud trail events according to start_time and resource_id
        @param event_type:
        @param start_time:
        @param resource_id:
        @param resource_type:
        @param end_time:
        @return: if user not found it return empty string

        """
        if start_time and not end_time:
            delay_seconds = int(os.environ.get('SLEEP_SECONDS', self.SLEEP_SECONDS))
            if self.__get_time_difference(start_time=start_time) <= delay_seconds:
                time.sleep(delay_seconds)
            search_time = timedelta(seconds=self.SEARCH_SECONDS)
            end_time = start_time + search_time
            start_time = start_time - search_time
        else:
            if not start_time and not end_time:
                start_time = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)
                end_time = datetime.now()
        username, event = self.__get_user_by_resource_id(start_time, end_time, resource_id, resource_type, event_type)
        return self.__check_filter_username(username, event)

    def get_username_from_resource_events(self, resource_id: str, iam_users: list,
                                         start_time: datetime = None, end_time: datetime = None,
                                         exclude_users: set = None):
        """
        Fallback username lookup: search ALL CloudTrail events for a resource
        and return the first username matching a known IAM user.
        Handles managed services (ROSA, EKS, etc.) where RunInstances is
        performed by a service account but subsequent events (CreateTags, etc.)
        may be performed by the actual user via SSO or IAM credentials.
        @param resource_id: The AWS resource ID to look up
        @param iam_users: List of known IAM usernames to validate against
        @param start_time: Optional search window start (defaults to LOOKBACK_DAYS ago)
        @param end_time: Optional search window end (defaults to now)
        @param exclude_users: Optional set of usernames to skip (automation accounts)
        @return: matching IAM username or empty string
        """
        if exclude_users is None:
            exclude_users = set()
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)
            if not end_time:
                end_time = datetime.now()
            responses = self.get_full_responses(
                StartTime=start_time, EndTime=end_time,
                LookupAttributes=[{
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': resource_id
                }])
            for event in responses:
                username, _ = self.__check_event_is_assumed_role(
                    event.get('CloudTrailEvent', ''))
                if username and username in iam_users and username not in exclude_users:
                    logger.info(f'Found username {username} from {event.get("EventName")} '
                                f'event on resource {resource_id}')
                    return username
                event_username = event.get('Username', '')
                if event_username and event_username in iam_users and event_username not in exclude_users:
                    logger.info(f'Found username {event_username} from {event.get("EventName")} '
                                f'event on resource {resource_id}')
                    return event_username
            return ''
        except Exception as err:
            logger.error(f'Error in get_username_from_resource_events: {err}')
            return ''

    def __get_username_from_role_cloudtrail(self, role: dict, iam_users: list):
        """
        Look up CloudTrail CreateRole event for a given IAM role and return
        the username if it matches a known IAM user.
        """
        role_name = role['RoleName']
        role_arn = role['Arn']
        create_date = role.get('CreateDate')
        if not create_date:
            return ''
        end_time = create_date + timedelta(seconds=self.SEARCH_SECONDS)
        start_time = create_date - timedelta(seconds=self.SEARCH_SECONDS)
        responses = self.__get_cloudtrail_responses(
            start_time=start_time, end_time=end_time,
            resource_arn=role_arn)
        for event in responses:
            if event.get('EventName') == 'CreateRole':
                username, _ = self.__check_event_is_assumed_role(
                    event.get('CloudTrailEvent', ''))
                if username and username in iam_users:
                    logger.info(f'Found cluster owner {username} from CreateRole '
                                f'event on role {role_name}')
                    return username
                event_username = event.get('Username', '')
                if event_username and event_username in iam_users:
                    logger.info(f'Found cluster owner {event_username} from CreateRole '
                                f'event on role {role_name}')
                    return event_username
        return ''

    def __get_username_from_create_role_events(self, start_time: datetime,
                                                end_time: datetime,
                                                iam_users: list):
        """
        Search CloudTrail for CreateRole events of OpenShift operator roles
        within a time window. Handles the case where roles were deleted from
        IAM but creation events still exist in CloudTrail (90-day retention).
        """
        try:
            events = self.__cloudtrail.lookup_events(
                LookupAttributes=[{
                    'AttributeKey': 'EventName',
                    'AttributeValue': 'CreateRole'
                }],
                StartTime=start_time, EndTime=end_time,
                MaxResults=50
            ).get('Events', [])
            for event in events:
                resources = event.get('Resources', [])
                role_names = [r.get('ResourceName', '') for r in resources
                              if r.get('ResourceType') == 'AWS::IAM::Role']
                if not any('openshift' in n.lower() for n in role_names):
                    continue
                username, _ = self.__check_event_is_assumed_role(
                    event.get('CloudTrailEvent', ''))
                if username and username in iam_users:
                    logger.info(f'Found cluster owner {username} from '
                                f'CloudTrail CreateRole event (deleted role)')
                    return username
                event_username = event.get('Username', '')
                if event_username and event_username in iam_users:
                    logger.info(f'Found cluster owner {event_username} from '
                                f'CloudTrail CreateRole event (deleted role)')
                    return event_username
        except Exception as err:
            logger.error(f'Error searching CreateRole events: {err}')
        return ''

    def get_username_from_cluster_role(self, cluster_id: str, iam_users: list,
                                       launch_time: datetime = None):
        """
        Trace a cluster's ownership through its IAM roles.
        Uses three strategies:
        1. Direct match: find roles whose names contain the cluster ID
           (works for IPI/UPI clusters)
        2. Temporal match: find ROSA/OpenShift operator roles created
           shortly before the cluster's instance launch time
           (works for ROSA STS where roles use cluster name, not infra ID)
        3. CloudTrail fallback: search CreateRole events directly for
           OpenShift roles in the time window (handles deleted roles)
        Works for both SSO (AssumedRole) and IAM user identities.
        @param cluster_id: The cluster infra ID (e.g. 'u0s3a7y7o5y9c6w-x56mc')
        @param iam_users: List of known IAM usernames to validate against
        @param launch_time: Instance launch time for temporal role matching
        @return: matching IAM username or empty string
        """
        ROSA_ROLE_WINDOW_SECONDS = 21600  # 6 hours before launch
        try:
            roles = self.__iam_client.list_roles(MaxItems=1000).get('Roles', [])
            cluster_roles = [r for r in roles if cluster_id in r.get('RoleName', '')]
            if cluster_roles:
                for role in cluster_roles:
                    username = self.__get_username_from_role_cloudtrail(role, iam_users)
                    if username:
                        return username

            if not launch_time:
                return ''
            candidate_roles = []
            for role in roles:
                role_name = role.get('RoleName', '')
                if 'openshift' not in role_name.lower():
                    continue
                create_date = role.get('CreateDate')
                if not create_date:
                    continue
                launch_naive = launch_time.replace(tzinfo=None)
                create_naive = create_date.replace(tzinfo=None)
                diff_seconds = (launch_naive - create_naive).total_seconds()
                if 0 <= diff_seconds <= ROSA_ROLE_WINDOW_SECONDS:
                    candidate_roles.append(role)
            if candidate_roles:
                candidate_roles.sort(key=lambda r: r.get('CreateDate', ''), reverse=True)
                for role in candidate_roles[:6]:
                    username = self.__get_username_from_role_cloudtrail(role, iam_users)
                    if username:
                        return username

            ct_start = launch_time - timedelta(seconds=ROSA_ROLE_WINDOW_SECONDS)
            username = self.__get_username_from_create_role_events(
                start_time=ct_start, end_time=launch_time,
                iam_users=iam_users)
            if username:
                return username
            return ''
        except Exception as err:
            logger.error(f'Error in get_username_from_cluster_role: {err}')
            return ''

    def get_stop_time(self, resource_id: str, event_name: str):
        """
        This method return the time of when instance is stopped
        @param resource_id:
        @param event_name:
        @return:
        """
        responses = []
        try:
            response = self.__cloudtrail.lookup_events(LookupAttributes=[
                {'AttributeKey': 'ResourceName', 'AttributeValue': resource_id},
            ])
            responses.extend(response['Events'])
            while response.get('NextToken'):
                response = self.__cloudtrail.lookup_events(LookupAttributes=[
                    {'AttributeKey': 'ResourceName', 'AttributeValue': resource_id},
                ], NextToken=response.get('NextToken'))
                responses.extend(response['Events'])

            for event in responses:
                if event.get('EventName') == event_name:
                    if event.get('Resources'):
                        for resource in event.get('Resources'):
                            if resource.get('ResourceName') == resource_id:
                                return event.get('EventTime')
            return ''
        except:
            return ''

    def set_cloudtrail(self, region_name: str):
        self.__cloudtrail = boto3.client('cloudtrail', region_name=region_name)

    def get_last_time_accessed(self, resource_id: str, event_name: str, start_time: datetime, end_time: datetime, **kwargs):
        """
        This method return last accesses time
        @param resource_id:
        @param event_name:
        @param start_time:
        @param end_time:
        @return:
        """
        try:
            events = self.__cloudtrail.lookup_events(StartTime=start_time, EndTime=end_time, LookupAttributes=[{
                'AttributeKey': 'ResourceName', 'AttributeValue': resource_id
            }])['Events']
            if events:
                events = sorted(events, key=lambda event: event['EventTime'], reverse=True)
                events = [event for event in events if event.get('EventName') not in ('CreateTags', 'DeleteTags')]
                if events:
                    if events[0].get('EventName') == event_name:
                        return events[0].get('EventTime')
                if kwargs:
                    if len(events) == 1:
                        if events[0].get('EventName') == kwargs['optional_event_name'][0]:
                            return events[0].get('EventTime')
                    elif len(events) == 2:
                        if events[0].get('EventName') in kwargs['optional_event_name'] and events[1].get('EventName') in kwargs['optional_event_name']:
                            return events[0].get('EventTime')
            else:
                return start_time - timedelta(days=4)
        except Exception as err:
            logger.info(f'{err}')
            return None
        return None
