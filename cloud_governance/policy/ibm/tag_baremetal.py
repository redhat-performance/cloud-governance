
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.policy.policy_operations.ibm.tagging.tagging_operations import TaggingOperations


class TagBareMetal(TaggingOperations):
    """
    This class tags IBM Bare metal machines
    """

    def __init__(self):
        super().__init__()

    def get_hardware_username(self, hardware_id: str):
        """
        This method returns the hardware_username form the order details
        @param hardware_id:
        @return:
        """
        hardware_data = self._classic_operations.get_hardware_data(hardware_id=str(hardware_id))
        if hardware_data:
            return hardware_data.get('billingItem').get('orderItem').get('order').get('userRecord').get('username'), f'{hardware_data.get("hostname")}.{hardware_data.get("domain")}'
        return '', ''

    def tag_remove_hardware(self, user_tags: list, hardware_tags: list, hardware_id: str, hardware_name: str):
        """
        This method removes the hardware tags
        @param user_tags:
        @param hardware_tags:
        @param hardware_id:
        @param hardware_name:
        @return:
        """
        remove_hardware_tags = self._filter_remove_tags(user_tags=user_tags, resource_tags=hardware_tags)
        if self._tag_remove_name:
            remove_hardware_tags = [self._tag_remove_name]
        if remove_hardware_tags:
            try:
                response = self.softlayer_operation(softlayer_name='SoftLayer_Hardware_Server', softlayer_method='removeTags', resource_id=hardware_id, tags=','.join(remove_hardware_tags))
                if response:
                    logger.info(f'Tags are Removed to the hardware: {hardware_id} - {hardware_name} : count: {len(remove_hardware_tags)} : {remove_hardware_tags}')
                else:
                    logger.info(f'Tags are not Removed to the Hardware: {hardware_id} - {hardware_name}, something might fail')
            except Exception as err:
                logger.info(f'{err}')
        return remove_hardware_tags

    def tag_update_hardware(self, user_tags: list, hardware_tags: list, hardware_id: str, hardware_name: str):
        """
        This method sets the hardware tags
        @param user_tags:
        @param hardware_tags:
        @param hardware_id:
        @param hardware_name:
        @return:
        """
        add_hardware_tags = []
        if self._tag_custom:
            add_hardware_tags.extend(self._tag_custom)
        add_hardware_tags.extend(self._filter_common_tags(user_tags=user_tags, resource_tags=hardware_tags))
        if add_hardware_tags:
            if self._tag_operation == 'update':
                add_hardware_tags.extend(hardware_tags)
                add_hardware_tags = list(set(add_hardware_tags))
                try:
                    response = self.softlayer_operation(softlayer_name='SoftLayer_Hardware_Server', softlayer_method='setTags', resource_id=hardware_id, tags=','.join(add_hardware_tags))
                    if response:
                        logger.info(f'Tags are added to the hardware: {hardware_id} - {hardware_name} : count: {len(add_hardware_tags)} : {add_hardware_tags}')
                    else:
                        logger.info(f'Tags are not added to the hardware: {hardware_id} - {hardware_name}, something might fail')
                except Exception as err:
                    logger.info(f'{err}')
        return add_hardware_tags

    def tag_hardware(self, hardware_id: str):
        """
        This method perform tag operations - update, remove read
        @param hardware_id:
        @return:
        """
        username, hardware_name = self.get_hardware_username(hardware_id=hardware_id)
        if username and hardware_name:
            hardware_tags = self._classic_operations.get_hardware_tags(hardware_id=str(hardware_id))
            user_tags = self._ibm_client.get_user_tags_from_gsheet(username=username)
            if self._tag_operation == 'remove':
                tags = self.tag_remove_hardware(user_tags, hardware_tags, hardware_id, hardware_name)
            else:
                tags = self.tag_update_hardware(user_tags, hardware_tags, hardware_id, hardware_name)
            return tags
        return []

    @logger_time_stamp
    def run(self, hardware_id: str = ''):
        """
        This method tag hardware ( bare-metals ) from the user tags from the gsheet
        @return:
        """
        response = []
        if hardware_id:
            response = self.tag_hardware(hardware_id=hardware_id)
        else:
            hardware_ids = self._classic_operations.get_hardware_ids()
            for hardware_id in hardware_ids:
                response_data = self.tag_hardware(hardware_id=hardware_id.get('id'))
                if response_data:
                    response.append({hardware_id.get('hostname'): response_data})
        return response
