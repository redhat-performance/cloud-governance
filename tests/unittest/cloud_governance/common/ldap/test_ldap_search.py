from unittest.mock import patch

import ldap
from ldap.ldapobject import SimpleLDAPObject

from cloud_governance.common.ldap.ldap_search import LdapSearch


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
