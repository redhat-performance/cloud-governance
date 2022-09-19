
from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount


class ClassicOperations:
    """"
    This class is for IBM classic operations - BareMetal, Virtual Machines
    """

    def __init__(self):
        self._sl_client = IBMAccount().get_sl_client()

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

    def get_hardware_ids(self):
        """
        this method list all hardwares ( bare-metal machines) in ibm classic infrastructure devices
        @return:
        """
        hardware_mask = "mask[id, hostname]"
        hardware_ids = self._sl_client.call('Account', 'getHardware', mask=hardware_mask, iter=True)
        return hardware_ids

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

    def get_hardware_tags(self, hardware_id: str):
        """
        This method returns tags of hardware ( bare-metal machines )
        @param hardware_id:
        @return:
        """
        tags = self._sl_client.call('SoftLayer_Hardware_Server', 'getTagReferences', id=hardware_id)
        return self.__filter_tag_names(tag_references=tags)

    def get_virtual_machine_ids(self):
        """
        this method list all hardwares ( bare-metal machines) in ibm classic infrastructure devices
        @return:
        """
        vm_mask = "mask[id, hostname]"
        vm_ids = self._sl_client.call('Account', 'getVirtualGuests', mask=vm_mask, iter=True)
        return vm_ids

    def get_virtual_machine_data(self, vm_id: str):
        """
        This method return virtual machine from the hardware-id
        @param vm_id:
        @return:
        """
        mask = 'mask[billingItem[orderItem[order[userRecord[username]]]]]'
        vm_data = self._sl_client.call('SoftLayer_Virtual_Guest', 'getObject', id=vm_id, mask=mask)
        return vm_data

    def get_virtual_machine_tags(self, vm_id: str):
        """
        This method returns tags of hardware ( bare-metal machines )
        @param vm_id:
        @return:
        """
        tags = self._sl_client.call('SoftLayer_Virtual_Guest', 'getTagReferences', id=vm_id)
        return self.__filter_tag_names(tag_references=tags)
