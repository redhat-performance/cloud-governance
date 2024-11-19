from retry import retry
from typeguard import typechecked

from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount
from cloud_governance.common.jira.jira import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class ClassicOperations:
    """"
    This class is for IBM classic operations - BareMetal, Virtual Machines
    """

    RETRIES = 3
    DELAY = 30

    def __init__(self):
        self._sl_client = IBMAccount().get_sl_client()

    @typechecked
    def __filter_tag_names(self, tag_references: list):
        """
        This method filter tag names from the tagReferences
        @param tags:
        @return:
        """
        tags = []
        if tag_references:
            for tag in tag_references:
                tags.append(tag.get('tag')['name'].strip())
        return tags

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @logger_time_stamp
    def get_hardware_ids(self):
        """
        this method list all hardwares ( bare-metal machines) in ibm classic infrastructure devices
        @return:
        """
        hardware_mask = "mask[id, hostname, fullyQualifiedDomainName]"
        hardware_ids = self._sl_client.call('Account', 'getHardware', mask=hardware_mask, iter=True)
        return hardware_ids

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @typechecked
    def get_hardware_data(self, hardware_id: str):
        """
        This method return hardware_data from the hardware-id
        hardware --> bare-metal machine
        @param hardware_id:
        @return:
        """
        mask = 'mask[billingItem[orderItem[order[userRecord[username]]]]]'
        hardware_data = self._sl_client.call('SoftLayer_Hardware_Server', 'getObject', id=hardware_id, mask=mask)
        return hardware_data

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @typechecked
    def get_hardware_tags(self, hardware_id: str):
        """
        This method returns tags of hardware ( bare-metal machines )
        @param hardware_id:
        @return:
        """
        tags = self._sl_client.call('SoftLayer_Hardware_Server', 'getTagReferences', id=hardware_id)
        return self.__filter_tag_names(tag_references=tags)

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @logger_time_stamp
    def get_virtual_machine_ids(self):
        """
        this method list all hardwares ( bare-metal machines) in ibm classic infrastructure devices
        @return:
        """
        vm_mask = "mask[id, hostname, fullyQualifiedDomainName]"
        vm_ids = self._sl_client.call('Account', 'getVirtualGuests', mask=vm_mask, iter=True)
        return vm_ids

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @typechecked
    def get_virtual_machine_data(self, vm_id: str):
        """
        This method return virtual machine from the hardware-id
        @param vm_id:
        @return:
        """
        mask = 'mask[billingItem[orderItem[order[userRecord[username]]]]]'
        vm_data = self._sl_client.call('SoftLayer_Virtual_Guest', 'getObject', id=vm_id, mask=mask)
        return vm_data

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @typechecked
    def get_virtual_machine_tags(self, vm_id: str):
        """
        This method returns tags of hardware ( bare-metal machines )
        @param vm_id:
        @return:
        """
        tags = self._sl_client.call('SoftLayer_Virtual_Guest', 'getTagReferences', id=vm_id)
        return self.__filter_tag_names(tag_references=tags)

    def update_baremetal_tags(self, tags: list, hardware_id: str):
        """
        This method updates the hardware tags
        :param tags:
        :param hardware_id:
        :return:
        """
        tag_names = []
        for tag in tags:
            key, value = tag.split(':')
            tag_names.append(f"{key.strip()}:{value.strip()}")
        error = ''
        try:
            response = self._sl_client.call('SoftLayer_Hardware_Server',
                                            'setTags', ','.join(tag_names), id=hardware_id)
            if response:
                logger.info(f'Tags are added to the hardware: {hardware_id}  : {tag_names}')
            else:
                logger.error(
                    f'Tags are not added to the hardware: {hardware_id} - , something might fail')
        except Exception as err:
            error = str(err)
            response = False
            logger.error(f'{err}')
        return response, error

    def update_virtual_machine_tags(self, tags: list, virtual_machine_id: str):
        """
        This method updates the virtual machine tags
        :param tags:
        :param virtual_machine_id:
        :return:
        """
        tag_names = []
        for tag in tags:
            key, value = tag.split(':')
            tag_names.append(f"{key.strip()}:{value.strip()}")
        error = ''
        try:
            response = self._sl_client.call('SoftLayer_Virtual_Guest',
                                            'setTags', ','.join(tag_names), id=virtual_machine_id)
            if response:
                logger.info(f'Tags are added to the VirtualMachine: {virtual_machine_id}  : {tags}')
            else:
                logger.error(
                    f'Tags are not added to the VirtualMachine: {virtual_machine_id} - , something might fail')
        except Exception as err:
            error = str(err)
            response = False
            logger.error(f'{err}')
        return response, error
