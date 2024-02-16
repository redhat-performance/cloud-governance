from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkInterfaceIPConfiguration, PublicIPAddress, IPConfiguration

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.azure.cleanup.ip_unattached import IpUnattached
from tests.unittest.configs import SUBSCRIPTION_ID, CURRENT_DATE
from tests.unittest.mocks.azure.mock_compute.mock_compute import mock_compute
from tests.unittest.mocks.azure.mock_identity.mock_default_credential import MockDefaultAzureCredential
from tests.unittest.mocks.azure.mock_network.mock_network import mock_network


@mock_compute
@mock_network
def test_ip_unattached_using_addresses():
    """
    This method tests ip_unattached not collect the used ip addresses
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    ip_address = (network_client.public_ip_addresses.
                  begin_create_or_update(public_ip_address_name='test', location='useast',
                                         public_ip_address_version='IPv4',
                                         public_ip_allocation_method='Static'))
    network_interface = network_client.network_interfaces.begin_create_or_update(network_interface_name='unitest',
                                                                                 virtual_machine='test-unitest',
                                                                                 ip_configurations=[
                                                                                     NetworkInterfaceIPConfiguration(
                                                                                         id="interface-1",
                                                                                         public_ip_address=
                                                                                         PublicIPAddress(id=ip_address.id)
                                                                                     )
                                                                                 ])
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              ip_configuration=IPConfiguration(id=network_interface.id))
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 0


@mock_compute
@mock_network
def test_ip_unattached_skip_live_cluster_id():
    """
    This method tests ip_unattached policy skips the ip connected to active cluster
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    compute_client = ComputeManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    compute_client.virtual_machines.begin_create_or_update(vm_name='test-unitest', tags=tags, location='useast')
    ip_address = (network_client.public_ip_addresses.
                  begin_create_or_update(public_ip_address_name='test', location='useast',
                                         public_ip_address_version='IPv4',
                                         public_ip_allocation_method='Static', tags=tags))
    network_interface = network_client.network_interfaces.begin_create_or_update(network_interface_name='unitest',
                                                                                 virtual_machine='test-unittest',
                                                                                 ip_configurations=[
                                                                                     NetworkInterfaceIPConfiguration(
                                                                                         id="interface-1",
                                                                                         public_ip_address=
                                                                                         PublicIPAddress(
                                                                                             id=ip_address.id)
                                                                                     )
                                                                                 ], tags=tags)
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              ip_configuration=IPConfiguration(id=network_interface.id),
                                                              tags=tags)
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 0


@mock_compute
@mock_network
def test_ip_unattached_not_live_cluster_id():
    """
    This method tests ip_unattached policy collect ip not connected to active cluster
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    tags = {'kubernetes.io/cluster/unittest-vm': 'owned'}
    ip_address = (network_client.public_ip_addresses.
                  begin_create_or_update(public_ip_address_name='test', location='useast',
                                         public_ip_address_version='IPv4',
                                         public_ip_allocation_method='Static', tags=tags))
    network_interface = network_client.network_interfaces.begin_create_or_update(network_interface_name='unitest',
                                                                                 ip_configurations=[
                                                                                     NetworkInterfaceIPConfiguration(
                                                                                         id="interface-1",
                                                                                         public_ip_address=
                                                                                         PublicIPAddress(
                                                                                             id=ip_address.id)
                                                                                     )
                                                                                 ], tags=tags)
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              ip_configuration=IPConfiguration(id=network_interface.id),
                                                              tags=tags)
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1


@mock_compute
@mock_network
def test_ip_unattached_dry_run_yes():
    """
    This method tests ip_unattached, not attached to any instance or network interface
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static')
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0


@mock_compute
@mock_network
def test_ip_unattached_dryrun_no():
    """
    This method tests ip_unattached, not attached to any instance or network interface
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static')
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 1
    assert response[0]['ResourceState'] == 'disassociated'


@mock_compute
@mock_network
def test_ip_unattached_delete():
    """
    This method tests ip_unattached to delete ip address, not attached to any instance or network interface
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              tags={'DaysCount': f'{CURRENT_DATE}@7'})
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] == 'Deleted'


@mock_compute
@mock_network
def test_ip_unattached_skips_delete():
    """
    This method tests ip_unattached to delete ip address, not attached to any instance or network interface
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              tags={'DaysCount': f'{CURRENT_DATE}@7', 'Policy': 'skip'})
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 7
    assert response[0]['ResourceState'] == 'disassociated'


@mock_compute
@mock_network
def test_ip_unattached_set_counter_zero():
    """
    This method tests ip_unattached to set days counter to 0, not attached to any instance or network interface
    :return:
    :rtype:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    network_client = NetworkManagementClient(subscription_id=SUBSCRIPTION_ID, credential=MockDefaultAzureCredential())
    network_client.public_ip_addresses.begin_create_or_update(public_ip_address_name='test', location='useast',
                                                              public_ip_address_version='IPv4',
                                                              public_ip_allocation_method='Static',
                                                              tags={'DaysCount': f'{CURRENT_DATE}@7'})
    ip_unattached = IpUnattached()
    response = ip_unattached.run()
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
    assert response[0]['ResourceState'] == 'disassociated'
