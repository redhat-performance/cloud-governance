import datetime
from unittest.mock import patch, Mock

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.v2021_05_01.models import TimeSeriesElement, MetricValue
from azure.mgmt.resource import ResourceManagementClient

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.azure.cleanup.instance_idle import InstanceIdle
from cloud_governance.policy.azure.cleanup.instance_run import InstanceRun
from tests.unittest.configs import SUBSCRIPTION_ID, CURRENT_DATE
from tests.unittest.mocks.azure.mock_compute.mock_compute import mock_compute
from tests.unittest.mocks.azure.mock_computes import MockVirtualMachine, MockAzure
from tests.unittest.mocks.azure.mock_identity.mock_default_credential import MockDefaultAzureCredential
from tests.unittest.mocks.azure.mock_monitor.mock_monitor import mock_monitor
from tests.unittest.mocks.azure.mock_network.mock_network import mock_network


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle():
    """
    This method tests instance_idle returning or not
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      time_created=time_created)
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 1


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__check_not_idle():
    """
    This method tests instance_idle, check for not idle instances
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      time_created=time_created)
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=3)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 0


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__skip_cluster():
    """
    This method tests instance_idle not collect the active cluster resources
    :return:
    :rtype:
    """
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast', tags=tags,
                                                           time_created=time_created)
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 0


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__dryrun_no():
    """
    This method tests instance_idle dry_run no with non-idle instances
    :return:
    :rtype:
    """
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      tags=tags, time_created=time_created)
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=3)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=10000)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=10000)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 0


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__dryrun_no_delete():
    """
    This method tests stop the instance_idle
    :return:
    :rtype:
    """
    tags = {'DaysCount': f'{CURRENT_DATE}@7'}
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      tags=tags, time_created=time_created)
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] == 'Vm Stopped'


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__skips_delete():
    """
    This method tests skip deletion of instance_idle
    :return:
    :rtype:
    """
    tags = {'DaysCount': f'{CURRENT_DATE}@7', 'Policy': 'skip'}
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      tags=tags, time_created=time_created)
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] != 'Deleted'


@mock_compute
@mock_network
@mock_monitor
def test_instance_idle__set_counter_zero():
    """
    This method tests unused_nat_gateway to set days counter to 0
    :return:
    :rtype:
    """
    tags = {'DaysCount': f'{CURRENT_DATE}@7'}
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'instance_idle'
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    time_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(8)
    instance = compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', location='useast',
                                                                      tags=tags, time_created=time_created)
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-cpu-metric',
                                         unit='Percentage CPU',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-in-metric',
                                         unit='Network In Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    monitor_client.metrics.create_metric(resource_id=instance.id, type='VirtualMachine', name='test-network-out-metric',
                                         unit='Network Out Total',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.utcnow(), average=0)
                                         ])])
    instance_idle = InstanceIdle()
    response = instance_idle.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
