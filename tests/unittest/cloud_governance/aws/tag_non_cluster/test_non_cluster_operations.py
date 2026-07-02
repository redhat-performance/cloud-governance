from datetime import datetime, timezone
from unittest.mock import Mock

from cloud_governance.policy.policy_operations.aws.tag_non_cluster.non_cluster_operations import NonClusterOperations


def _make_non_cluster_ops(**overrides):
    ops = NonClusterOperations.__new__(NonClusterOperations)
    ops.iam_users = overrides.get('iam_users', ['pragchau', 'cloud-governance-delete-user'])
    ops._automation_user = overrides.get('_automation_user', 'cloud-governance-user')
    ops.get_user_name_from_name_tag = Mock(return_value=overrides.get('name_tag_user'))
    ops._get_username_from_cloudtrail = Mock(return_value=overrides.get('cloudtrail_user'))
    ops.cloudtrail = Mock()
    ops.cloudtrail.get_username_from_resource_events = Mock(
        return_value=overrides.get('resource_events_user', ''))
    return ops


class TestNonClusterOperationsGetUsername:
    START_TIME = datetime(2026, 6, 30, 14, 0, 0, tzinfo=timezone.utc)

    def test_excludes_automation_user_from_primary_cloudtrail(self):
        ops = _make_non_cluster_ops(cloudtrail_user='cloud-governance-user')
        result = ops.get_username(
            start_time=self.START_TIME, resource_id='vol-abc123',
            resource_type='AWS::EC2::Volume', tags=[])
        assert result == ''
        ops.cloudtrail.get_username_from_resource_events.assert_called_once()

    def test_returns_valid_user_from_primary_cloudtrail(self):
        ops = _make_non_cluster_ops(cloudtrail_user='pragchau')
        result = ops.get_username(
            start_time=self.START_TIME, resource_id='vol-abc123',
            resource_type='AWS::EC2::Volume', tags=[])
        assert result == 'pragchau'
        ops.cloudtrail.get_username_from_resource_events.assert_not_called()

    def test_resource_events_fallback_excludes_automation_user(self):
        ops = _make_non_cluster_ops(
            cloudtrail_user='',
            resource_events_user='pragchau')
        result = ops.get_username(
            start_time=self.START_TIME, resource_id='vol-abc123',
            resource_type='AWS::EC2::Volume', tags=[])
        assert result == 'pragchau'
        call_kwargs = ops.cloudtrail.get_username_from_resource_events.call_args.kwargs
        assert call_kwargs['exclude_users'] == {'cloud-governance-user'}
