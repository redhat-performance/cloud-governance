from unittest.mock import MagicMock

from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import \
    NonClusterZombiePolicy


def _make_instance():
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'ip_unattached'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    environment_variables.environment_variables_dict['EMAIL_ALERT'] = True
    environment_variables.environment_variables_dict['MANAGER_EMAIL_ALERT'] = True
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    with mock_aws():
        return NonClusterZombiePolicy()


@mock_aws
def test_trigger_mail_sends_successfully_when_ldap_lookup_fails():
    """
    This method tests the mail still sends when the LDAP lookup fails (returns [], not a
    dict) - previously this raised AttributeError ('list' object has no attribute 'get')
    before ever reaching send_email_postfix, so no email sent at all. MANAGER_EMAIL_ALERT
    is True (the default), which is the branch that previously crashed unconditionally.
    """
    policy = _make_instance()
    policy._mail = MagicMock()
    policy._ldap = MagicMock()
    policy._ldap.get_user_details.return_value = []
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Name', 'Value': 'test-resource'},
    ]
    policy._trigger_mail(tags=tags, resource_id='eipalloc-123', days=4, resource_type='PublicIPv4')
    policy._mail.send_email_postfix.assert_called_once()
    _, kwargs = policy._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'jdoe'
    assert not any('None@redhat.com' in str(c) for c in kwargs['cc'])


@mock_aws
def test_trigger_mail_still_ccs_manager_when_ldap_resolves():
    """
    This method tests the manager is still CC'd when the LDAP lookup succeeds, confirming
    the fix did not change behavior for the success path
    """
    policy = _make_instance()
    policy._mail = MagicMock()
    policy._ldap = MagicMock()
    policy._ldap.get_user_details.return_value = {'displayName': 'John Doe', 'managerId': 'jmanager'}
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Name', 'Value': 'test-resource'},
    ]
    policy._trigger_mail(tags=tags, resource_id='eipalloc-123', days=4, resource_type='PublicIPv4')
    _, kwargs = policy._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'jdoe'
    assert 'jmanager@redhat.com' in kwargs['cc']
