"""
Unit tests for cloud_governance.policy.aws.delete_access_key.DeleteAccessKey.
"""
from unittest.mock import patch

from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.delete_access_key import DeleteAccessKey
from cloud_governance.common.utils.configs import DELETE_ACCESS_KEY_DAYS
from tests.unittest.configs import DRY_RUN_YES, DRY_RUN_NO, AWS_DEFAULT_REGION, TEST_USER_NAME


def _mock_iam_users_inactive_key(
    age_days: int,
    last_activity_days: int = 130,
    with_inactive_tag: bool = True,
    access_key_id: str = 'AKIAIOSFODNN7EXAMPLE',
):
    """Build mock IAM user with one inactive access key, as returned by get_iam_users_access_keys()."""
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}]
    if with_inactive_tag:
        tags.append({'Key': 'UnusedAccessKey1InactiveDate', 'Value': '2024-01-15'})
    return {
        TEST_USER_NAME: {
            'Access key 1': {
                'label': 'Access key 1',
                'status': 'Inactive',
                'age_days': age_days,
                'last_activity_days': last_activity_days,
                'access_key_id': access_key_id,
            },
            'tags': tags,
            'region': AWS_DEFAULT_REGION,
            'ResourceId': 'AIDAEXAMPLE',
        }
    }


@mock_aws
def test_delete_access_key_skips_active_keys():
    """Only inactive keys are considered; active keys are skipped."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_inactive_key(age_days=DELETE_ACCESS_KEY_DAYS + 10, with_inactive_tag=True)
    mock_data[TEST_USER_NAME]['Access key 1']['status'] = 'Active'
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_delete_access_key_skips_when_age_at_or_below_threshold():
    """Inactive keys with age_days <= DELETE_ACCESS_KEY_DAYS are skipped."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_inactive_key(age_days=DELETE_ACCESS_KEY_DAYS, with_inactive_tag=True)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_delete_access_key_includes_inactive_old_key_with_tag():
    """Inactive key with age > DELETE_ACCESS_KEY_DAYS and UnusedAccessKey1InactiveDate tag is included."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    age_days = DELETE_ACCESS_KEY_DAYS + 5
    mock_data = _mock_iam_users_inactive_key(age_days=age_days, with_inactive_tag=True)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 1
    assert result[0]['ResourceId'] == TEST_USER_NAME
    # ES schema stores cleanup_result in ResourceAction (dry_run=yes -> verify returns False)
    assert result[0]['ResourceAction'] == 'False'
    assert result[0]['ResourceType'] == 'UnusedAccessKey'
    assert result[0]['ResourceState'] == 'Inactive'
    assert result[0]['AgeDays'] == age_days


@mock_aws
def test_delete_access_key_skips_inactive_old_key_without_tag_unless_flag():
    """Inactive key with age > threshold but no UnusedAccessKey1InactiveDate tag is skipped unless DELETE_INACTIVE_KEYS_WITHOUT_TAG."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict.pop('DELETE_INACTIVE_KEYS_WITHOUT_TAG', None)

    mock_data = _mock_iam_users_inactive_key(age_days=DELETE_ACCESS_KEY_DAYS + 10, with_inactive_tag=False)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_delete_access_key_includes_inactive_old_key_without_tag_when_flag_set():
    """When DELETE_INACTIVE_KEYS_WITHOUT_TAG is True, inactive keys over threshold are included even without tag."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['DELETE_INACTIVE_KEYS_WITHOUT_TAG'] = True

    age_days = DELETE_ACCESS_KEY_DAYS + 10
    mock_data = _mock_iam_users_inactive_key(age_days=age_days, with_inactive_tag=False)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 1
    assert result[0]['ResourceId'] == TEST_USER_NAME
    # ES schema stores cleanup_result in ResourceAction (dry_run=yes -> verify returns False)
    assert result[0]['ResourceAction'] == 'False'
    assert result[0]['AgeDays'] == age_days


@mock_aws
def test_delete_access_key_empty_when_no_users():
    """When no IAM users have access keys, result is empty."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value={}):
        policy = DeleteAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_delete_access_key_deletion_grace_days_capped():
    """Deletion grace days is min(age_days - DELETE_ACCESS_KEY_DAYS, DAYS_TO_TAKE_ACTION)."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    age_days = DELETE_ACCESS_KEY_DAYS + 20
    mock_data = _mock_iam_users_inactive_key(age_days=age_days, with_inactive_tag=True)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(DeleteAccessKey, 'verify_and_delete_resource', return_value=False) as mock_verify:
            policy = DeleteAccessKey()
            policy.run_policy_operations()
            call_kwargs = mock_verify.call_args[1]
            assert call_kwargs['clean_up_days'] == 7
            assert call_kwargs['access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
            assert call_kwargs['remove_inactive_tag'] is True


@mock_aws
def test_delete_access_key_remove_inactive_tag_false_when_no_tag():
    """When key has no UnusedAccessKey1InactiveDate tag, verify_and_delete_resource is called with remove_inactive_tag=False."""
    environment_variables.environment_variables_dict['policy'] = 'delete_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['DELETE_INACTIVE_KEYS_WITHOUT_TAG'] = True

    mock_data = _mock_iam_users_inactive_key(age_days=DELETE_ACCESS_KEY_DAYS + 5, with_inactive_tag=False)
    with patch.object(DeleteAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(DeleteAccessKey, 'verify_and_delete_resource', return_value=False) as mock_verify:
            policy = DeleteAccessKey()
            policy.run_policy_operations()
            call_kwargs = mock_verify.call_args[1]
            assert call_kwargs['remove_inactive_tag'] is False
