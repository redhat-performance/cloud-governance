from cloud_governance.common.logger.init_logger import logger
from cloud_governance.ibm.tagging.tagging_operations import TaggingOperations


class TagVM(TaggingOperations):
    """
    This class tags IBM virtual machines
    """

    def __init__(self):
        super().__init__()

    def get_virtual_machine_username(self, vm_id: str):
        """
        This method return the virtual machine username from the billing order lists
        @param vm_id:
        @return:
        """
        vm_data = self._classic_operations.get_virtual_machine_data(vm_id=str(vm_id))
        return vm_data.get('billingItem').get('orderItem').get('order').get('userRecord').get('username'), f'{vm_data.get("hostname")}.{vm_data.get("domain")}'

    def tag_update_virtual_machine(self, user_tags: list, vm_tags: list, vm_id: str, vm_name: str):
        """
        this method updates th etags of the virtual machine
        @param user_tags:
        @param vm_tags:
        @param vm_id:
        @param vm_name:
        @return:
        """
        add_vm_tags = []
        if self._tag_custom:
            add_vm_tags.extend(self._tag_custom)
        add_vm_tags.extend(self._filter_common_tags(user_tags=user_tags, resource_tags=vm_tags))
        if add_vm_tags:
            tags = add_vm_tags
            if self._tag_operation == 'update':
                add_vm_tags.extend(vm_tags)
                add_vm_tags = list(set(add_vm_tags))
                try:
                    response = self.softlayer_operation(softlayer_name='SoftLayer_Virtual_Guest', softlayer_method='setTags', tags=','.join(add_vm_tags), resource_id=vm_id)
                    if response:
                        logger.info(f'Tags are added to the vm: {vm_id} - {vm_name} : count: {len(tags)} : {tags}')
                    else:
                        logger.info(f'Tags are not added to the vm: {vm_id} - {vm_name}, something might fail')
                except Exception as err:
                    logger.info(f'{err}')
        return add_vm_tags

    def tag_remove_virtual_machine(self, user_tags: list, vm_tags: list, vm_id: str, vm_name: str):
        """
        This method returns the tags of the virtual machine
        @param user_tags:
        @param vm_tags:
        @param vm_id:
        @param vm_name:
        @return:
        """
        remove_vm_tags = self._filter_remove_tags(user_tags=user_tags, resource_tags=vm_tags)
        if self._tag_remove_name:
            remove_vm_tags = [self._tag_remove_name]
        if remove_vm_tags:
            try:
                response = self.softlayer_operation(softlayer_name='SoftLayer_Virtual_Guest', softlayer_method='removeTags', tags=','.join(remove_vm_tags), resource_id=vm_id)
                if response:
                    logger.info(f'Tags are Removed to the vm: {vm_id} - {vm_name} : count: {len(remove_vm_tags)} : {remove_vm_tags}')
                else:
                    logger.info(f'Tags are not Removed to the vm: {vm_id} - {vm_name}, something might fail')
            except Exception as err:
                logger.info(f'{err}')
        return remove_vm_tags

    def tag_virtual_machine(self, vm_id: str):
        """
        This method perform the tag operations - read, update, remove
        @param vm_id:
        @return:
        """
        username, vm_name = self.get_virtual_machine_username(vm_id=vm_id)
        vm_tags = self._classic_operations.get_virtual_machine_tags(vm_id=str(vm_id))
        user_tags = self._ibm_client.get_user_tags_from_gsheet(username=username)
        if self._tag_operation == 'remove':
            tags = self.tag_remove_virtual_machine(user_tags=user_tags, vm_tags=vm_tags, vm_id=vm_id, vm_name=vm_name)
        else:
            tags = self.tag_update_virtual_machine(user_tags=user_tags, vm_tags=vm_tags, vm_id=vm_id, vm_name=vm_name)
        return tags

    def run(self, vm_id: str = ''):
        """
        This method tag vm ( virtual machines ) from the user tags from the gsheet
        @return:
        """
        response = []
        if vm_id:
            response = self.tag_virtual_machine(vm_id=vm_id)
        else:
            vm_ids = self._classic_operations.get_virtual_machine_ids()
            for vm_id in vm_ids:
                response.append({vm_id.get('hostname'): self.tag_virtual_machine(vm_id=vm_id.get('id'))})
        return response
