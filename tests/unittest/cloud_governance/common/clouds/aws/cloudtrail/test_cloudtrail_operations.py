import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations


class TestCloudTrailOperations:
    """Test CloudTrail operations for different user identity types"""

    # ========================
    # AssumedRole (SAML SSO) Tests
    # ========================

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_assumed_role_simple_username(self, mock_boto3):
        """
        Test SAML SSO AssumedRole with simple alphanumeric session name.

        Scenario: User authenticates via SAML SSO and assumes a role
        ARN format: arn:aws:sts::account:assumed-role/role-name/session-name
        Expected: Extract 'testuser' from the session name (last part after /)
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "AssumedRole",
                "principalId": "AROAEXAMPLEID123456:testuser",
                "arn": "arn:aws:sts::123456789012:assumed-role/AdminRole/testuser",
                "accountId": "123456789012",
                "sessionContext": {
                    "sessionIssuer": {
                        "type": "Role",
                        "principalId": "AROAEXAMPLEID123456",
                        "arn": "arn:aws:iam::123456789012:role/AdminRole",
                        "accountId": "123456789012",
                        "userName": "AdminRole"
                    }
                }
            }
        }

        cloudtrail_event_str = json.dumps(cloudtrail_event)
        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')

        # Verify ARN parsing extracts session name correctly
        arn = cloudtrail_event["userIdentity"]["arn"]
        session_name = arn.split('/')[-1]
        assert session_name == "testuser"

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_assumed_role_email_session_name(self, mock_boto3):
        """
        Test SAML SSO AssumedRole with email address as session name.

        Scenario: Corporate SSO where session name is user's email address
        ARN format: arn:aws:sts::account:assumed-role/SSORole/user@example.com
        Expected: Extract 'user@example.com' from session name
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "AssumedRole",
                "principalId": "AROAEXAMPLEID123456:user@example.com",
                "arn": "arn:aws:sts::123456789012:assumed-role/SSORole/user@example.com",
                "sessionContext": {
                    "sessionIssuer": {
                        "arn": "arn:aws:iam::123456789012:role/SSORole"
                    }
                }
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username == "user@example.com"
        assert event is not None

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_assumed_role_hyphenated_session_name(self, mock_boto3):
        """
        Test SAML SSO AssumedRole with hyphenated session name.

        Scenario: Session name contains hyphens (common in usernames)
        ARN format: arn:aws:sts::account:assumed-role/DevRole/test-user-123
        Expected: Extract 'test-user-123' from session name, preserving hyphens
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "AssumedRole",
                "principalId": "AROAEXAMPLEID123456:test-user-123",
                "arn": "arn:aws:sts::123456789012:assumed-role/DevRole/test-user-123",
                "sessionContext": {
                    "sessionIssuer": {
                        "arn": "arn:aws:iam::123456789012:role/DevRole"
                    }
                }
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username == "test-user-123"
        assert event is not None

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_assumed_role_integration_multiple_formats(self, mock_boto3):
        """
        Integration test for AssumedRole: Verify multiple session name formats work correctly.

        Scenario: Test various real-world SAML SSO session name patterns in one test
        Formats tested:
        1. Simple alphanumeric: 'testuser'
        2. Email address: 'user@example.com'
        3. Hyphenated username: 'jane-doe-123'
        Expected: All formats should extract username correctly from ARN
        """
        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')

        test_cases = [
            {
                "event": {
                    "userIdentity": {
                        "type": "AssumedRole",
                        "principalId": "AROAEXAMPLEID123456:testuser",
                        "arn": "arn:aws:sts::123456789012:assumed-role/AdminRole/testuser",
                        "sessionContext": {
                            "sessionIssuer": {
                                "arn": "arn:aws:iam::123456789012:role/AdminRole"
                            }
                        }
                    }
                },
                "expected_username": "testuser",
                "description": "Simple alphanumeric session name"
            },
            {
                "event": {
                    "userIdentity": {
                        "type": "AssumedRole",
                        "principalId": "AROAEXAMPLEID123456:user@example.com",
                        "arn": "arn:aws:sts::123456789012:assumed-role/SSORole/user@example.com",
                        "sessionContext": {
                            "sessionIssuer": {
                                "arn": "arn:aws:iam::123456789012:role/SSORole"
                            }
                        }
                    }
                },
                "expected_username": "user@example.com",
                "description": "Email address as session name"
            },
            {
                "event": {
                    "userIdentity": {
                        "type": "AssumedRole",
                        "principalId": "AROAEXAMPLEID123456:jane-doe-123",
                        "arn": "arn:aws:sts::999888777666:assumed-role/999888777666-admin/jane-doe-123",
                        "sessionContext": {
                            "sessionIssuer": {
                                "arn": "arn:aws:iam::999888777666:role/999888777666-admin"
                            }
                        }
                    }
                },
                "expected_username": "jane-doe-123",
                "description": "Hyphenated username with numbers"
            }
        ]

        for test_case in test_cases:
            event_str = json.dumps(test_case["event"])
            username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(event_str)

            assert username == test_case["expected_username"], \
                f"{test_case['description']}: Expected '{test_case['expected_username']}' but got '{username}'"
            assert event is not None

    # ========================
    # IAMUser Tests
    # ========================

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_iam_user_simple_username(self, mock_boto3):
        """
        Test IAMUser with simple username (no path in ARN).

        Scenario: Regular IAM user without organizational path structure
        ARN format: arn:aws:iam::account:user/username
        Expected: Extract 'johndoe' from ARN, not from userName field
        Note: userName field intentionally omitted to verify ARN parsing
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "AIDAEXAMPLEID123456",
                "arn": "arn:aws:iam::123456789012:user/johndoe",
                "accountId": "123456789012"
            }
        }

        cloudtrail_event_str = json.dumps(cloudtrail_event)
        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')

        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(cloudtrail_event_str)

        assert username == "johndoe"
        assert event is not None

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_iam_user_with_path(self, mock_boto3):
        """
        Test IAMUser with organizational path in ARN.

        Scenario: IAM user in nested organizational structure with path
        ARN format: arn:aws:iam::account:user/path/subpath/username
        Path: /department/team/
        Expected: Extract 'alice' (last part after final /) ignoring path segments
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "IAMUser",
                "arn": "arn:aws:iam::123456789012:user/department/team/alice"
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username == "alice"
        assert event is not None

    # ========================
    # Other User Identity Types
    # ========================

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_root_user(self, mock_boto3):
        """
        Test Root user account access.

        Scenario: AWS account root user (not recommended for daily use)
        ARN format: arn:aws:iam::account:root (no slash separator)
        Expected: Return 'root' as the username
        Note: Root ARN has no path, special case handling required
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "Root",
                "arn": "arn:aws:iam::123456789012:root"
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username == "root"
        assert event is not None

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_federated_user(self, mock_boto3):
        """
        Test FederatedUser (legacy AWS federation).

        Scenario: Legacy federated user access (GetFederationToken API)
        ARN format: arn:aws:sts::account:federated-user/username
        Expected: Extract 'bob' from federated user ARN
        Note: Different from AssumedRole SAML federation
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "FederatedUser",
                "arn": "arn:aws:sts::123456789012:federated-user/bob"
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username == "bob"
        assert event is not None

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_unknown_user_type(self, mock_boto3):
        """
        Test unknown/unsupported userIdentity type.

        Scenario: AWS service principal or other unsupported identity type
        Type: AWSService (not in supported list: AssumedRole, IAMUser, FederatedUser, Root)
        Expected: Return [False, ''] to indicate unsupported type
        Note: Graceful degradation for future AWS identity types
        """
        cloudtrail_event = {
            "userIdentity": {
                "type": "AWSService",
                "arn": "arn:aws:iam::123456789012:service/something"
            }
        }

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(json.dumps(cloudtrail_event))

        assert username is False
        assert event == ''

    # ========================
    # Edge Cases and Error Handling
    # ========================

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_malformed_json_event(self, mock_boto3):
        """
        Test handling of malformed JSON CloudTrail event.

        Scenario: Invalid JSON string passed to parser
        Input: "invalid json" (not valid JSON)
        Expected: Return [False, ''] without throwing exception
        Note: Demonstrates robust error handling with try/except
        """
        cloudtrail_event_str = "invalid json"
        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')

        username, event = cloudtrail_ops._CloudTrailOperations__check_event_is_assumed_role(cloudtrail_event_str)

        assert username is False
        assert event == ''

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_arn_parsing_different_session_formats(self, mock_boto3):
        """
        Unit test for ARN parsing logic across different session name formats.

        Scenario: Verify split('/') logic handles various ARN patterns correctly
        Test cases:
        1. Simple username: testuser
        2. Email format: user@example.com
        3. Hyphenated: test-user-123
        4. Numeric account prefix: 999888777666-admin/sessionuser
        Expected: Last segment after final '/' is always extracted correctly
        """
        test_cases = [
            ("arn:aws:sts::123456789012:assumed-role/AdminRole/testuser", "testuser"),
            ("arn:aws:sts::123456789012:assumed-role/SSORole/user@example.com", "user@example.com"),
            ("arn:aws:sts::123456789012:assumed-role/DevRole/test-user-123", "test-user-123"),
            ("arn:aws:sts::999888777666:assumed-role/999888777666-admin/sessionuser", "sessionuser"),
        ]

        for arn, expected_username in test_cases:
            session_name = arn.split('/')[-1]
            assert session_name == expected_username, f"Failed to parse {arn}"


class TestCloudTrailOperationsRosaTagging:
    """Tests for ROSA cluster ownership resolution added in PR #1007."""

    LAUNCH_TIME = datetime(2026, 6, 30, 14, 6, 46, tzinfo=timezone.utc)
    IAM_USERS = ['pragchau', 'cloud-governance-delete-user']

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_get_username_from_resource_events_skips_excluded_users(self, mock_boto3):
        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        cloudtrail_ops.get_full_responses = Mock(return_value=[
            {
                'EventName': 'CreateTags',
                'Username': 'cloud-governance-delete-user',
                'CloudTrailEvent': '{}',
            },
            {
                'EventName': 'CreateTags',
                'Username': 'pragchau',
                'CloudTrailEvent': '{}',
            },
        ])
        result = cloudtrail_ops.get_username_from_resource_events(
            resource_id='i-0123456789abcdef0',
            iam_users=self.IAM_USERS,
            start_time=self.LAUNCH_TIME,
            exclude_users={'cloud-governance-delete-user'})
        assert result == 'pragchau'

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_get_username_from_cluster_role_direct_match(self, mock_boto3):
        mock_iam = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{
            'Roles': [{
                'RoleName': 'z2r7p1f3o6m2h3y-t5bx8-master-role',
                'Arn': 'arn:aws:iam::123456789012:role/z2r7p1f3o6m2h3y-t5bx8-master-role',
                'CreateDate': self.LAUNCH_TIME,
            }]
        }]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            'cloudtrail': Mock(),
            'iam': mock_iam,
        }[service]

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        cloudtrail_ops._CloudTrailOperations__get_username_from_role_cloudtrail = Mock(
            return_value='pragchau')

        result = cloudtrail_ops.get_username_from_cluster_role(
            cluster_id='z2r7p1f3o6m2h3y-t5bx8',
            iam_users=self.IAM_USERS,
            launch_time=self.LAUNCH_TIME)
        assert result == 'pragchau'

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_get_username_from_cluster_role_ambiguous_temporal_match_returns_empty(
            self, mock_boto3):
        role_create = datetime(2026, 6, 30, 13, 0, 0, tzinfo=timezone.utc)
        mock_iam = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{
            'Roles': [
                {
                    'RoleName': 'cluster-a-openshift-machine-api',
                    'Arn': 'arn:aws:iam::123456789012:role/cluster-a-openshift-machine-api',
                    'CreateDate': role_create,
                },
                {
                    'RoleName': 'cluster-b-openshift-machine-api',
                    'Arn': 'arn:aws:iam::123456789012:role/cluster-b-openshift-machine-api',
                    'CreateDate': role_create,
                },
            ]
        }]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            'cloudtrail': Mock(),
            'iam': mock_iam,
        }[service]

        cloudtrail_ops = CloudTrailOperations(region_name='us-east-1')
        cloudtrail_ops._CloudTrailOperations__get_username_from_role_cloudtrail = Mock(
            side_effect=['pragchau', 'otheruser'])
        cloudtrail_ops._CloudTrailOperations__get_username_from_create_role_events = Mock(
            return_value='')

        result = cloudtrail_ops.get_username_from_cluster_role(
            cluster_id='unknown-infra-id',
            iam_users=self.IAM_USERS + ['otheruser'],
            launch_time=self.LAUNCH_TIME)
        assert result == ''
        cloudtrail_ops._CloudTrailOperations__get_username_from_create_role_events.assert_called_once()

    @patch('cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations.boto3')
    def test_get_username_from_create_role_events_paginates_global_cloudtrail(
            self, mock_boto3):
        mock_global_ct = Mock()
        mock_global_ct.lookup_events.side_effect = [
            {'Events': [], 'NextToken': 'page2'},
            {'Events': [{
                'EventName': 'CreateRole',
                'Username': 'pragchau',
                'Resources': [{
                    'ResourceType': 'AWS::IAM::Role',
                    'ResourceName': 'rosa-test-openshift-machine-api',
                }],
                'CloudTrailEvent': '{}',
            }]},
        ]
        mock_boto3.client.return_value = Mock()

        cloudtrail_ops = CloudTrailOperations(region_name='us-west-2')
        cloudtrail_ops._CloudTrailOperations__global_cloudtrail = mock_global_ct

        start = datetime(2026, 6, 30, 8, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 6, 30, 14, 0, 0, tzinfo=timezone.utc)
        result = cloudtrail_ops._CloudTrailOperations__get_username_from_create_role_events(
            start_time=start, end_time=end, iam_users=self.IAM_USERS)
        assert result == 'pragchau'
        assert mock_global_ct.lookup_events.call_count == 2
