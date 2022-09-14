
import os.path
from cloud_governance.policy.ibm.tag_baremetal import TagBareMetal
from tests.unittest.cloud_governance.common.clouds.ibm.ibm_mock import ibm_mock


@ibm_mock
def test_tag_update_hardware():
    """
    This method tests the update tags of the hardware
    @return:
    """
    os.environ['tag_operation'] = 'update'
    tags = ['test:tags', 'user:athiuma']
    tag_baremetal = TagBareMetal()
    assert len(tag_baremetal.tag_update_hardware(user_tags=tags, hardware_tags=[], hardware_id='', hardware_name='')) == 2


@ibm_mock
def test_tag_remove_hardware():
    """
    This method tests the remove tags of the hardware
    @return:
    """
    tags = ['test:tags', 'user:athiuma']
    os.environ['tag_operation'] = 'update'
    tag_baremetal = TagBareMetal()
    tag_baremetal.tag_update_hardware(user_tags=tags, hardware_tags=[], hardware_id='', hardware_name='')
    tag_baremetal._tag_operation = 'remove'
    assert len(tag_baremetal.tag_remove_hardware(user_tags=tags, hardware_tags=tags, hardware_id='', hardware_name='')) == 2
