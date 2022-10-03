
import os.path
from cloud_governance.policy.ibm.tag_vm import TagVM
from tests.unittest.cloud_governance.common.clouds.ibm.ibm_mock import ibm_mock


@ibm_mock
def test_tag_update_virtual_machine():
    """
    This method  tests update the tags of the virtual machine
    @return:
    """
    os.environ['tag_operation'] = 'update'
    tags = ['test_tags:vm', 'user:athiuma']
    tag_vm = TagVM()
    assert len(tag_vm.tag_update_virtual_machine(user_tags=tags, vm_tags=[], vm_id='', vm_name='')) == 2


@ibm_mock
def test_tag_remove_virtual_machine():
    """
    This method tests removes the tags of the virtual machine
    @return:
    """
    tags = ['test_tags:vm', 'user:athiuma']
    os.environ['tag_operation'] = 'update'
    tag_vm = TagVM()
    tag_vm.tag_update_virtual_machine(user_tags=tags, vm_tags=[], vm_id='', vm_name='')
    tag_vm._tag_operation = 'remove'
    remove_tags = ['test_tags:vm']
    assert len(tag_vm.tag_remove_virtual_machine(user_tags=remove_tags, vm_tags=tags, vm_id='', vm_name='')) == 2
