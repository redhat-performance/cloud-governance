from datetime import datetime, timezone
from unittest.mock import Mock, patch

from cloud_governance.policy.policy_operations.aws.tag_cluster.tag_cluster_operations import TagClusterOperations


def _make_tag_cluster_ops(**overrides):
    """Build TagClusterOperations without calling __init__ (avoids real AWS calls)."""
    ops = TagClusterOperations.__new__(TagClusterOperations)
    ops.iam_users = overrides.get('iam_users', ['pragchau', 'cloud-governance-delete-user'])
    ops._automation_user = overrides.get('_automation_user', 'cloud-governance-user')
    ops.get_user_name_from_name_tag = Mock(return_value=overrides.get('name_tag_user'))
    ops._get_username_from_instance_id_and_time = Mock(
        return_value=overrides.get('instance_ct_user'))
    ops.cloudtrail = Mock()
    ops.cloudtrail.get_username_from_cluster_role = Mock(
        return_value=overrides.get('cluster_role_user', ''))
    ops._regional_cloudtrail = Mock()
    ops._regional_cloudtrail.get_username_from_resource_events = Mock(
        return_value=overrides.get('resource_events_user', ''))
    return ops


class TestTagClusterOperationsGetUsername:
    LAUNCH_TIME = datetime(2026, 6, 30, 14, 6, 46, tzinfo=timezone.utc)
    RESOURCE_ID = 'i-0123456789abcdef0'
    CLUSTER_ID = 'z2r7p1f3o6m2h3y-t5bx8'

    def test_returns_autoscaling_without_iam_validation(self):
        ops = _make_tag_cluster_ops(instance_ct_user='AutoScaling')
        result = ops.get_username(
            start_time=self.LAUNCH_TIME, resource_id=self.RESOURCE_ID,
            resource_type='AWS::EC2::Instance', tags=[], cluster_id=self.CLUSTER_ID)
        assert result == 'AutoScaling'

    def test_skips_automation_user_from_instance_cloudtrail(self):
        ops = _make_tag_cluster_ops(
            instance_ct_user='cloud-governance-user',
            cluster_role_user='pragchau')
        result = ops.get_username(
            start_time=self.LAUNCH_TIME, resource_id=self.RESOURCE_ID,
            resource_type='AWS::EC2::Instance', tags=[], cluster_id=self.CLUSTER_ID)
        assert result == 'pragchau'
        ops.cloudtrail.get_username_from_cluster_role.assert_called_once()

    def test_cluster_role_resolved_before_resource_events_fallback(self):
        ops = _make_tag_cluster_ops(
            instance_ct_user='178000000000',
            cluster_role_user='pragchau',
            resource_events_user='cloud-governance-delete-user')
        result = ops.get_username(
            start_time=self.LAUNCH_TIME, resource_id=self.RESOURCE_ID,
            resource_type='AWS::EC2::Instance', tags=[], cluster_id=self.CLUSTER_ID)
        assert result == 'pragchau'
        ops._regional_cloudtrail.get_username_from_resource_events.assert_not_called()

    def test_resource_events_fallback_excludes_automation_user(self):
        ops = _make_tag_cluster_ops(
            instance_ct_user='178000000000',
            cluster_role_user='',
            resource_events_user='pragchau')
        result = ops.get_username(
            start_time=self.LAUNCH_TIME, resource_id=self.RESOURCE_ID,
            resource_type='AWS::EC2::Instance', tags=[], cluster_id=self.CLUSTER_ID)
        assert result == 'pragchau'
        call_kwargs = ops._regional_cloudtrail.get_username_from_resource_events.call_args.kwargs
        assert call_kwargs['exclude_users'] == {'cloud-governance-user'}


class TestTagClusterOperationsClusterInstanceFallback:
    def test_get_username_from_cluster_instances_returns_tagged_peer(self):
        ops = TagClusterOperations.__new__(TagClusterOperations)
        ops.cluster_prefix = ['kubernetes.io/cluster/']
        ops.iam_users = ['pragchau']
        ops.ec2_operations = Mock()
        ops.ec2_operations.get_tag_value_from_tags = Mock(return_value='pragchau')
        resources = [[{
            'Tags': [
                {'Key': 'kubernetes.io/cluster/z2r7p1f3o6m2h3y-t5bx8', 'Value': 'owned'},
                {'Key': 'User', 'Value': 'pragchau'},
            ]
        }]]
        result = ops.get_username_from_cluster_instances(
            resources=resources, cluster_name='z2r7p1f3o6m2h3y-t5bx8')
        assert result == 'pragchau'
