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


@patch.object(SimpleLDAPObject, 'start_tls_s')
def test_ldaps_scheme_skips_start_tls(mock_start_tls):
    """
    This method tests an ldaps:// URI does not attempt StartTLS
    """
    LdapSearch(ldap_host_name='ldaps://ipa.redhat.com')
    mock_start_tls.assert_not_called()


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch.object(SimpleLDAPObject, 'simple_bind_s')
def test_no_bind_attempted_when_credentials_not_configured(mock_bind, mock_start_tls):
    """
    This method tests construction does not attempt a bind when no service-account
    credentials are configured
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''
    LdapSearch(ldap_host_name='example.com')
    mock_bind.assert_not_called()


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch.object(SimpleLDAPObject, 'simple_bind_s')
def test_binds_with_service_account_when_configured(mock_bind, mock_start_tls):
    """
    This method tests construction binds with the configured service-account credentials
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = 'uid=svc-account,dc=redhat,dc=com'
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = 'secret'
    LdapSearch(ldap_host_name='example.com')
    mock_bind.assert_called_once_with('uid=svc-account,dc=redhat,dc=com', 'secret')
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch.object(SimpleLDAPObject, 'simple_bind_s', side_effect=ldap.INVALID_CREDENTIALS())
def test_bind_failure_does_not_raise(mock_bind, mock_start_tls):
    """
    This method tests a bind failure is logged rather than raised
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = 'uid=svc-account,dc=redhat,dc=com'
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = 'wrong'
    LdapSearch(ldap_host_name='example.com')
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''


@patch.object(SimpleLDAPObject, 'simple_bind_s')
@patch.object(SimpleLDAPObject, 'start_tls_s', side_effect=ldap.LDAPError())
def test_bind_skipped_when_tls_failed(mock_start_tls, mock_bind):
    """
    This method tests the bind is skipped when StartTLS failed
    """
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = 'uid=svc-account,dc=redhat,dc=com'
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = 'secret'
    LdapSearch(ldap_host_name='example.com')
    mock_bind.assert_not_called()
    environment_variables.environment_variables_dict['LDAP_BIND_DN'] = ''
    environment_variables.environment_variables_dict['LDAP_BIND_PASSWORD'] = ''


@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
@patch.object(SimpleLDAPObject, 'start_tls_s', side_effect=ldap.LDAPError())
def test_lookup_blocked_when_tls_failed(mock_start_tls):
    """
    This method tests lookups are skipped, not run unencrypted, when StartTLS failed
    """
    ldap_object = LdapSearch(ldap_host_name='example.com')
    assert ldap_object._LdapSearch__get_details(user_name='test') == []


@patch('cloud_governance.common.ldap.ldap_search.ldap.initialize')
def test_bare_hostname_is_wrapped_as_ldap_uri(mock_initialize):
    """
    This method tests a bare hostname is wrapped as ldap://<host>
    """
    LdapSearch(ldap_host_name='ldap.corp.redhat.com')
    mock_initialize.assert_called_once_with('ldap://ldap.corp.redhat.com')


@patch('cloud_governance.common.ldap.ldap_search.ldap.initialize')
def test_full_uri_is_used_as_is(mock_initialize):
    """
    This method tests a value that already specifies a scheme is used as-is, not double-wrapped
    """
    LdapSearch(ldap_host_name='ldap:///dc=ipa,dc=redhat,dc=com')
    mock_initialize.assert_called_once_with('ldap:///dc=ipa,dc=redhat,dc=com')


@patch.object(SimpleLDAPObject, 'start_tls_s')
@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
def test_get_details_uses_configured_base_dn(mock_start_tls):
    """
    This method tests __get_details searches the configured LDAP_BASE_DN
    """
    environment_variables.environment_variables_dict['LDAP_BASE_DN'] = 'cn=accounts,dc=ipa,dc=redhat,dc=com'
    ldap_object = LdapSearch(ldap_host_name='example.com')
    result = ldap_object._LdapSearch__get_details(user_name='test')
    assert list(result.keys()) == ['displayName', 'manager', 'cn']
    environment_variables.environment_variables_dict['LDAP_BASE_DN'] = 'dc=redhat, dc=com'


@patch.object(SimpleLDAPObject, 'start_tls_s')
def test_get_details_logs_failure_as_warning(mock_start_tls, caplog):
    """
    This method tests a failed lookup is logged at WARNING level, not INFO
    """
    with patch.object(SimpleLDAPObject, 'search_s', side_effect=Exception('boom')):
        ldap_object = LdapSearch(ldap_host_name='example.com')
        with caplog.at_level('WARNING'):
            ldap_object._LdapSearch__get_details(user_name='test')
    assert any('boom' in record.message for record in caplog.records)
