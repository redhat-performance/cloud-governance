import datetime
from datetime import  UTC

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.v2021_05_01.models import TimeSeriesElement, MetricValue
from azure.mgmt.network import NetworkManagementClient

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.azure.cleanup.unused_nat_gateway import UnUsedNatGateway
from tests.unittest.configs import SUBSCRIPTION_ID, CURRENT_DATE, NAT_GATEWAY_NAME
from tests.unittest.mocks.azure.mock_compute.mock_compute import mock_compute
from tests.unittest.mocks.azure.mock_identity.mock_default_credential import MockDefaultAzureCredential
from tests.unittest.mocks.azure.mock_monitor.mock_monitor import mock_monitor
from tests.unittest.mocks.azure.mock_network.mock_network import mock_network


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__check_unused():
    """
    This method tests ip_unattached not collect the unused_nat_gateways
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(credential='', subscription_id='')
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount', timeseries=[])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__check_used():
    """
    This method tests ip_unattached not collect the used_nat_gateways
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(credential='', subscription_id='')
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=100)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 0


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__skip_live_cluster_id():
    """
    This method tests unused_natgateway not collect the active cluster resources
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', tags=tags, location='useast')
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 0


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__collect_not_live_cluster_id():
    """
    This method tests  collect the non-active cluster unused_nat_gateways
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__dryrun_no():
    """
    This method tests unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert response[0]['CleanUpDays'] == 1


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__dryrun_no_delete():
    """
    This method tests deletion of unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'DaysCount': f'{CURRENT_DATE}@7'}
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] == 'Deleted'


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__skips_delete():
    """
    This method tests skip deletion of unused_nat_gateway
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'DaysCount': f'{CURRENT_DATE}@7', 'Policy': 'skip'}
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] != 'Deleted'


@mock_compute
@mock_network
@mock_monitor
def test_unused_nat_gateway__set_counter_zero():
    """
    This method tests  unused_nat_gateway to set days counter to 0
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'unused_nat_gateway'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    monitor_client = MonitorManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'DaysCount': f'{CURRENT_DATE}@7'}
    nat_gateway = network_client.nat_gateways.begin_create_or_update(nat_gateway_name=NAT_GATEWAY_NAME, tags=tags)
    monitor_client.metrics.create_metric(resource_id=nat_gateway.id, type='NatGateway', name='test-metric',
                                         unit='SNATConnectionCount',
                                         timeseries=[TimeSeriesElement(data=[
                                             MetricValue(time_stamp=datetime.datetime.now(UTC.utc), average=0)
                                         ])])
    unused_nat_gateway = UnUsedNatGateway()
    response = unused_nat_gateway.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
