

class CloudTrail:

    def __init__(self):
        pass

    def __get_username_from_events(self, events: list, resource_type: str, resource_id: str):
        for event in events:
            if event.get('Resources'):
                for resource in event.get('Resources'):
                    if resource.get('ResourceType') == resource_type:
                        if resource.get('ResourceName') == resource_id:
                            username, assumed_event = self.__check_event_is_assumed_role(event.get('CloudTrailEvent'))
                            if username:
                                return [username, assumed_event]
                            return [event.get('Username'), event]

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