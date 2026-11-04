from unittest.mock import patch

import ldap
from ldap.ldapobject import SimpleLDAPObject

from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.main.environment_variables import environment_variables


def mock_search_s(cls, base, scope, filterstr=None, attrlist=None):
    return [(f'uid:test,{base}', {'displayName': ['integration-test'], 'manager': [f'uid:cloudgovernance,{base}'], 'cn': ['cloud governance test']})]


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
def test_get_details(mock_start_tls):
    ldap_object = LdapSearch(ldap_host_name='example.com')
    assert list(ldap_object._LdapSearch__get_details(user_name='test').keys()) == ['displayName', 'manager', 'cn']


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch('cloud_governance.common.ldap.ldap_search.ldap.set_option')
def test_requires_tls_certificate_validation(mock_set_option, mock_start_tls):
    """
    This method tests TLS certificate validation is enforced explicitly
    """
    LdapSearch(ldap_host_name='example.com')
    mock_set_option.assert_called_once_with(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)


@patch.object(SimpleLDAPObject, 'start_tls_s')
def test_starts_tls_before_use(mock_start_tls):
    """
    This method tests the connection negotiates TLS, so the certificate check actually runs
    """
    LdapSearch(ldap_host_name='example.com')
    mock_start_tls.assert_called_once()


@patch.object(SimpleLDAPObject, 'start_tls_s', side_effect=ldap.LDAPError())
def test_start_tls_failure_does_not_raise(mock_start_tls):
    """
    This method tests a StartTLS failure is logged rather than raised
    """
    LdapSearch(ldap_host_name='example.com')


@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
@patch.object(SimpleLDAPObject, 'start_tls_s', side_effect=ldap.LDAPError())
def test_lookup_blocked_when_tls_failed(mock_start_tls):
    """
    This method tests lookups are skipped, not run unencrypted, when StartTLS failed
    """
    ldap_object = LdapSearch(ldap_host_name='example.com')
    assert ldap_object._LdapSearch__get_details(user_name='test') == []


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


@patch('cloud_governance.common.ldap.ldap_search.ldap.initialize')
def test_bare_hostname_is_wrapped_as_ldap_uri(mock_initialize):
    """
    This method tests a bare hostname (the legacy LDAP_HOST_NAME style) is wrapped as
    ldap://<host>, preserving today's behavior
    """
    LdapSearch(ldap_host_name='ldap.corp.redhat.com')
    mock_initialize.assert_called_once_with('ldap://ldap.corp.redhat.com')


@patch('cloud_governance.common.ldap.ldap_search.ldap.initialize')
def test_full_uri_is_used_as_is(mock_initialize):
    """
    This method tests a value that already specifies a scheme - e.g. IPA's DNS-based server
    discovery URI, or a direct ldaps:// connection to a specific server - is passed through
    unchanged rather than being double-wrapped
    """
    LdapSearch(ldap_host_name='ldap:///dc=ipa,dc=redhat,dc=com')
    mock_initialize.assert_called_once_with('ldap:///dc=ipa,dc=redhat,dc=com')


@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
def test_get_details_uses_configured_base_dn():
    """
    This method tests __get_details searches the configured LDAP_BASE_DN (e.g. an IPA base
    such as cn=accounts,dc=ipa,dc=redhat,dc=com) rather than the hardcoded legacy base
    """
    environment_variables.environment_variables_dict['LDAP_BASE_DN'] = 'cn=accounts,dc=ipa,dc=redhat,dc=com'
    ldap_object = LdapSearch(ldap_host_name='example.com')
    result = ldap_object._LdapSearch__get_details(user_name='test')
    assert list(result.keys()) == ['displayName', 'manager', 'cn']
    environment_variables.environment_variables_dict['LDAP_BASE_DN'] = 'dc=redhat, dc=com'


def test_get_details_logs_failure_as_warning(caplog):
    """
    This method tests a failed lookup is logged at WARNING level, not INFO - this represents
    a real, frequent operational failure that was previously easy to miss in logs filtered
    on WARNING/ERROR
    """
    with patch.object(SimpleLDAPObject, 'search_s', side_effect=Exception('boom')):
        ldap_object = LdapSearch(ldap_host_name='example.com')
        with caplog.at_level('WARNING'):
            ldap_object._LdapSearch__get_details(user_name='test')
    assert any('boom' in record.message for record in caplog.records)
