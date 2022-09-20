from unittest.mock import patch

from ldap.ldapobject import SimpleLDAPObject

from cloud_governance.common.ldap.ldap_search import LdapSearch


def mock_search_s(cls, base, scope, filterstr=None, attrlist=None):
    return [(f'uid:test,{base}', {'displayName': ['integration-test'], 'manager': [f'uid:cloudgovernance,{base}'], 'cn': ['cloud governance test']})]


@patch.object(SimpleLDAPObject, 'search_s', mock_search_s)
def test_get_details():
    ldap_object = LdapSearch(ldap_host_name='example.com')
    assert list(ldap_object.get_details(user_name='test').keys()) == ['displayName', 'manager', 'cn']
