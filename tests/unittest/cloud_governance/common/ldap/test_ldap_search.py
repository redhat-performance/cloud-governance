from unittest.mock import patch

import ldap
from ldap.ldapobject import SimpleLDAPObject

from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.main.environment_variables import environment_variables


def mock_search_s(cls, base, scope, filterstr=None, attrlist=None):
    return [(f'uid:test,{base}', {'displayName': ['integration-test'], 'manager': [f'uid:cloudgovernance,{base}'], 'cn': ['cloud governance test']})]


@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
def test_get_details():
    ldap_object = LdapSearch(ldap_host_name='example.com')
    assert list(ldap_object._LdapSearch__get_details(user_name='test').keys()) == ['displayName', 'manager', 'cn']


@patch.object(SimpleLDAPObject, 'simple_bind_s')
def test_no_bind_attempted_when_credentials_not_configured(mock_bind):
    """
    This method tests construction does not attempt a bind when no service-account
    credentials are configured, preserving today's anonymous-bind behavior
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''
    LdapSearch(ldap_host_name='example.com')
    mock_bind.assert_not_called()


@patch.object(SimpleLDAPObject, 'simple_bind_s')
def test_binds_with_service_account_when_configured(mock_bind):
    """
    This method tests construction binds with the configured service-account credentials
    rather than relying on an anonymous bind, which Red Hat's LDAP server rejects
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = 'uid=svc-account,dc=redhat,dc=com'
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = 'secret'
    LdapSearch(ldap_host_name='example.com')
    mock_bind.assert_called_once_with('uid=svc-account,dc=redhat,dc=com', 'secret')
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''


@patch.object(SimpleLDAPObject, 'simple_bind_s', side_effect=ldap.INVALID_CREDENTIALS())
def test_bind_failure_does_not_raise(mock_bind):
    """
    This method tests a bind failure (e.g. a stale or wrong service-account credential) is
    logged rather than raised, since this runs during Postfix/MailMessage construction and
    an uncaught error here would crash the whole policy run, not just one LDAP lookup
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = 'uid=svc-account,dc=redhat,dc=com'
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = 'wrong'
    LdapSearch(ldap_host_name='example.com')
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''
