from unittest.mock import Mock, patch

from azure.mgmt.compute import ComputeManagementClient

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.azure.cleanup.unattached_volume import UnattachedVolume
from tests.unittest.mocks.azure.mock_compute import MockDisk, MockAzure, MockVirtualMachine


def test_unattached_volume_dry_run_yes_0_unattached():
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    mock_disk1 = MockDisk(disk_state='Attached', disk_size_gb=4)
    mock_azure = MockAzure(disks=[mock_disk1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) == 0


def test_unattached_volume_dry_run_yes():
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    mock_disk1 = MockDisk(disk_state='Unattached', disk_size_gb=4)
    mock_azure = MockAzure(disks=[mock_disk1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) > 0
        response = response[0]
        assert response.get('ResourceDelete') == 'False'
        assert response.get('SkipPolicy') == 'NA'


def test_unattached_volume_dry_run_no():
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    mock_disk1 = MockDisk(disk_state='Unattached', disk_size_gb=4)
    mock_azure = MockAzure(disks=[mock_disk1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) > 0
        response = response[0]
        assert response.get('ResourceDelete') == 'True'
        assert response.get('SkipPolicy') == 'NA'


def test_unattached_volume_dry_run_no_7_days_action():
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    mock_disk1 = MockDisk(disk_state='Unattached', disk_size_gb=4)
    mock_azure = MockAzure(disks=[mock_disk1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) > 0
        response = response[0]
        assert response.get('ResourceDelete') == 'False'
        assert response.get('SkipPolicy') == 'NA'


def test_unattached_volume_dry_run_no_skip():
    tags = {'Policy': 'notdelete'}
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    mock_disk1 = MockDisk(disk_state='Unattached', disk_size_gb=4, tags=tags)
    mock_azure = MockAzure(disks=[mock_disk1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) > 0
        response = response[0]
        assert response.get('ResourceDelete') == 'False'
        assert response.get('SkipPolicy') == 'NOTDELETE'


def test_check_exists_cluster():
    """
    This tests verify skip the existing cluster volume
    :return:
    :rtype:
    """
    tags = {'kubernetes.io/cluster/test': 'owned'}
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    mock_disk1 = MockDisk(disk_state='Unattached', disk_size_gb=4, tags=tags)
    mock_vm1 = MockVirtualMachine(tags=tags)
    mock_azure = MockAzure(disks=[mock_disk1], vms=[mock_vm1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list.side_effect = mock_azure.mock_list_disks
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    with patch.object(ComputeManagementClient, 'disks', mock_virtual_machines), \
         patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        volume_run = UnattachedVolume()
        response = volume_run.run()
        assert len(response) == 0
