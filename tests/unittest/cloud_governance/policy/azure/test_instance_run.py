import datetime
from unittest.mock import patch, Mock

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.azure.cleanup.instance_run import InstanceRun
from tests.unittest.mocks.azure.mock_computes import MockVirtualMachine, MockAzure


def test_instance_run():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    vm1 = MockVirtualMachine(tags={'User': 'mock'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines = Mock()
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        response = response[0]
        assert 'DryRun' in response.keys()
        assert 'False' == response['ResourceStopped']


def test_instance_run_stop_false():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        assert 'DryRun' in response[0].keys()
        assert 1 == response[0]['CleanUpDays']
        assert 'False' == response[0]['ResourceStopped']


def test_instance_run_stopped():
    """
    This method tests instance_run
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 0
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.begin_deallocate.side_effect = Mock()
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        assert 'DryRun' in response[0].keys()
        assert 1 == response[0]['CleanUpDays']
        assert 'True' == response[0]['ResourceStopped']


def test_instance_run_stopped_skip():
    """
    This method tests instance_run skip
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 0
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock', 'Policy': 'notdelete'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        assert 'DryRun' in response[0].keys()
        assert 'NOTDELETE' == response[0]['SkipPolicy'].upper()
        assert 1 == response[0]['CleanUpDays']
        assert 'False' == response[0]['ResourceStopped']


def test_instance_run_stopped_test_days():
    """
    This method tests instance_run skip
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    date = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).date()
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock', 'Policy': 'notdelete',
                                   'DaysCount': f'{date}@1'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    mock_tags = Mock()
    mock_tags.begin_create_or_update_at_scope.side_effect = mock_tags
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines), \
            patch.object(ResourceManagementClient, 'tags', mock_tags):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        assert 'DryRun' in response[0].keys()
        assert 2 == response[0]['CleanUpDays']
        assert 'NOTDELETE' == response[0]['SkipPolicy'].upper()
        assert 'False' == response[0]['ResourceStopped']


def test_instance_run_stopped_test_current_day():
    """
    This method tests instance_run skip
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    date = (datetime.datetime.utcnow()).date()
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock', 'Policy': 'notdelete',
                                   'DaysCount': f'{date}@1'})
    mock_azure = MockAzure(vms=[vm1])
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    mock_tags = Mock()
    mock_tags.begin_create_or_update_at_scope.side_effect = mock_tags
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines), \
            patch.object(ResourceManagementClient, 'tags', mock_tags):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 1
        assert 'DryRun' in response[0].keys()
        assert 1 == response[0]['CleanUpDays']
        assert 'NOTDELETE' == response[0]['SkipPolicy'].upper()
        assert 'False' == response[0]['ResourceStopped']


def test_instance_run_vm_already_stopped():
    """
    This method tests instance_run already stopped
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 3
    environment_variables.environment_variables_dict['policy'] = 'instance_run'
    environment_variables.environment_variables_dict['SHUTDOWN_PERIOD'] = True
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    date = (datetime.datetime.utcnow()).date()
    mock_virtual_machines = Mock()
    vm1 = MockVirtualMachine(tags={'User': 'mock', 'Policy': 'notdelete',
                                   'DaysCount': f'{date}@1'})
    mock_azure = MockAzure(vms=[vm1], status2="Vm Stopped")
    mock_virtual_machines.list_all.side_effect = mock_azure.mock_list_all
    mock_virtual_machines.instance_view.side_effect = mock_azure.mock_instance_view
    mock_tags = Mock()
    mock_tags.begin_create_or_update_at_scope.side_effect = mock_tags
    with patch.object(ComputeManagementClient, 'virtual_machines', mock_virtual_machines), \
            patch.object(ResourceManagementClient, 'tags', mock_tags):
        instance_run = InstanceRun()
        response = instance_run.run()
        assert len(response) == 0
