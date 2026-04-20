"""
Unit tests for cloud_governance.policy.aws.unused_access_key.UnusedAccessKey.
"""
from unittest.mock import patch

from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.unused_access_key import UnusedAccessKey
from cloud_governance.common.utils.configs import UNUSED_ACCESS_KEY_DAYS
from tests.unittest.configs import DRY_RUN_YES, DRY_RUN_NO, AWS_DEFAULT_REGION, TEST_USER_NAME


def _mock_iam_users_access_keys(age_days: int, status: str = 'Active', last_activity_days: int = 100):
    """Build mock IAM users access keys dict as returned by IAMOperations.get_iam_users_access_keys()."""
    return {
        TEST_USER_NAME: {
            'Access key 1': {
                'label': 'Access key 1',
                'status': status,
                'age_days': age_days,
                'last_activity_days': last_activity_days,
                'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            },
            'tags': [{'Key': 'User', 'Value': TEST_USER_NAME}],
            'region': AWS_DEFAULT_REGION,
            'ResourceId': 'AIDAEXAMPLE',
        }
    }


@mock_aws
def test_unused_access_key_skips_when_age_below_threshold():
    """Keys with age_days < UNUSED_ACCESS_KEY_DAYS are skipped (no deactivation)."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_access_keys(age_days=UNUSED_ACCESS_KEY_DAYS - 1, status='Active')
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=True):
            policy = UnusedAccessKey()
            result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_unused_access_key_includes_when_age_at_or_above_threshold():
    """Keys with age_days >= UNUSED_ACCESS_KEY_DAYS are included for deactivation path."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_access_keys(age_days=UNUSED_ACCESS_KEY_DAYS, status='Active')
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=True):
            policy = UnusedAccessKey()
            result = policy.run_policy_operations()
    assert len(result) == 1
    assert result[0]['ResourceId'] == TEST_USER_NAME
    # ES schema stores cleanup_result in ResourceAction (dry_run=yes -> verify returns False)
    assert result[0]['ResourceAction'] == 'False'
    assert result[0]['ResourceType'] == 'UnusedAccessKey'
    assert result[0]['AgeDays'] == UNUSED_ACCESS_KEY_DAYS


@mock_aws
def test_unused_access_key_skips_inactive_keys():
    """Keys with status 'Inactive' are skipped."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_access_keys(age_days=UNUSED_ACCESS_KEY_DAYS + 10, status='Inactive')
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=False):
            policy = UnusedAccessKey()
            result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_unused_access_key_skips_when_skip_policy_tag():
    """Users with Policy=notdelete or skip are skipped."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_access_keys(age_days=UNUSED_ACCESS_KEY_DAYS + 5, status='Active')
    mock_data[TEST_USER_NAME]['tags'] = [
        {'Key': 'User', 'Value': TEST_USER_NAME},
        {'Key': 'Policy', 'Value': 'not-delete'},
    ]
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=True):
            policy = UnusedAccessKey()
            result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_unused_access_key_skips_when_no_active_keys():
    """When _has_active_access_keys returns False for the key, it is skipped."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    mock_data = _mock_iam_users_access_keys(age_days=UNUSED_ACCESS_KEY_DAYS + 5, status='Active')
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=False):
            policy = UnusedAccessKey()
            result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_unused_access_key_empty_when_no_users():
    """When no IAM users have access keys, result is empty."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value={}):
        policy = UnusedAccessKey()
        result = policy.run_policy_operations()
    assert len(result) == 0


@mock_aws
def test_unused_access_key_deactivation_grace_days_capped():
    """Deactivation grace days is min(age_days - UNUSED_ACCESS_KEY_DAYS, DAYS_TO_TAKE_ACTION)."""
    environment_variables.environment_variables_dict['policy'] = 'unused_access_key'
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7

    age_days = UNUSED_ACCESS_KEY_DAYS + 20
    mock_data = _mock_iam_users_access_keys(age_days=age_days, status='Active')
    with patch.object(UnusedAccessKey, '_get_iam_users_access_keys', return_value=mock_data):
        with patch.object(UnusedAccessKey, '_has_active_access_keys', return_value=True):
            with patch.object(UnusedAccessKey, 'verify_and_delete_resource', return_value=False) as mock_verify:
                policy = UnusedAccessKey()
                policy.run_policy_operations()
                call_kwargs = mock_verify.call_args[1]
                # grace = min(20, 7) = 7
                assert call_kwargs['clean_up_days'] == 7
