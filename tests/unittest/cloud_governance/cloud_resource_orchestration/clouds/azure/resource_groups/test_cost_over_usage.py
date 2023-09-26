from cloud_governance.cloud_resource_orchestration.clouds.azure.resource_groups.cost_over_usage import CostOverUsage
from tests.unittest.cloud_governance.cloud_resource_orchestration.mocks.clouds.azure.mock_subscription import mock_subscription
from tests.unittest.cloud_governance.cloud_resource_orchestration.mocks.clouds.azure.mock_compute import mock_compute
from tests.unittest.cloud_governance.cloud_resource_orchestration.mocks.clouds.azure.mock_identity import mock_identity


@mock_subscription
@mock_identity
@mock_compute
def test_verify_active():
    """
    This method verifies returning True for the active resources
    :return:
    :rtype:
    """
    cost_over_usage = CostOverUsage()
    assert cost_over_usage._verify_active_resources(tag_name='user', tag_value='mock')


@mock_subscription
@mock_identity
@mock_compute
def test_verify_non_active():
    cost_over_usage = CostOverUsage()
    assert not cost_over_usage._verify_active_resources(tag_value='user', tag_name='test')

