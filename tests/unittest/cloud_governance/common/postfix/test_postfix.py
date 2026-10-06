from unittest.mock import MagicMock, patch

from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


def test_prettify_to():
    """
    This method tests the postfix to and cc
    :return:
    :rtype:
    """
    postfix = Postfix()
    response = postfix.prettify_to(to="test@redhat.com")
    assert response == "test@redhat.com"


def test_prettify_to_multiple_values():
    """
    This method tests the postfix to and cc
    :return:
    :rtype:
    """
    postfix = Postfix()
    response = postfix.prettify_to(to="test@redhat.com, test1")
    assert response == "test@redhat.com,test1@redhat.com"


def test_prettify_to_with_list():
    """
    This method tests the postfix to and cc
    :return:
    :rtype:
    """
    postfix = Postfix()
    response = postfix.prettify_to(to=["test@redhat.com", "test1"])
    assert response == "test@redhat.com,test1@redhat.com"


def test_prettify_cc():
    """
    This method tests the cc
    :return:
    :rtype:
    """
    postfix = Postfix()
    response = postfix.prettify_cc(cc=["test@redhat.com", "test1"])
    assert "test@redhat.com" in response
    assert "test1@redhat.com" in response


def test_prettify_cc_with_to():
    """
    This method tests the cc
    :return:
    :rtype:
    """
    postfix = Postfix()
    response = postfix.prettify_cc(cc=["test@redhat.com", "test1"], to="test1, test")
    assert not response


def test_prettify_to_rejects_domain_substring_bypass():
    """
    A value that merely contains '@redhat.com' as a substring (not as its actual
    domain suffix) must not be mistaken for an already-complete address.
    """
    postfix = Postfix()
    response = postfix.prettify_to(to="victim@redhat.com.evil.com")
    assert response == "victim@redhat.com.evil.com@redhat.com"


def test_prettify_cc_rejects_domain_substring_bypass():
    """
    Same domain-substring-bypass guard for cc
    """
    postfix = Postfix()
    response = postfix.prettify_cc(cc=["victim@redhat.com.evil.com"])
    assert response == "victim@redhat.com.evil.com@redhat.com"


def test_prettify_to_preserves_non_default_allowed_domain():
    """
    When ALLOWED_EMAIL_DOMAINS is configured with a non-redhat.com domain, an
    address already on that domain must be preserved, not appended with
    '@redhat.com'.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@example.com']
    try:
        postfix = Postfix()
        response = postfix.prettify_to(to="team@example.com")
        assert response == "team@example.com"
    finally:
        environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']


def test_prettify_cc_preserves_non_default_allowed_domain():
    """
    Same non-default-domain preservation guard for cc
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@example.com']
    try:
        postfix = Postfix()
        response = postfix.prettify_cc(cc=["team@example.com"])
        assert response == "team@example.com"
    finally:
        environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']


def test_prettify_to_still_appends_default_domain_for_bare_values():
    """
    A bare value not on any allowed domain still gets the default '@redhat.com'
    appended, even when ALLOWED_EMAIL_DOMAINS includes other domains.
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@example.com', '@redhat.com']
    try:
        postfix = Postfix()
        response = postfix.prettify_to(to="jdoe")
        assert response == "jdoe@redhat.com"
    finally:
        environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']


def _make_postfix(default_admins=None):
    """
    This method builds a Postfix instance configured for send_email_postfix tests, with the
    LDAP client swapped for a MagicMock so no real LDAP connection is attempted.
    """
    environment_variables.environment_variables_dict['EMAIL_ALERT'] = True
    environment_variables.environment_variables_dict['EMAIL_TO'] = ''
    environment_variables.environment_variables_dict['EMAIL_CC'] = ''
    environment_variables.environment_variables_dict['DEFAULT_ADMINS'] = default_admins or [
        'admin1@redhat.com', 'admin2@redhat.com']
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['PERF_SERVICES_URL'] = ''
    postfix = Postfix()
    postfix._Postfix__ldap_search = MagicMock()
    return postfix


def _sent_cc(mock_smtp):
    return mock_smtp.return_value.__enter__.return_value.send_message.call_args[0][0]['Cc']


@patch('cloud_governance.common.mails.postfix.smtplib.SMTP')
def test_send_email_postfix_skips_admin_cc_for_email_shaped_recipient(mock_smtp):
    """
    This method tests a resolved Email-tag recipient (individual or Rover/team group) is not
    CC'd to the default admins just because it doesn't resolve as an LDAP username - that
    LDAP uid lookup was never a meaningful check for an already-qualified address, and firing
    it anyway would needlessly broadcast every Email-tag-routed alert to the default admins.
    """
    postfix = _make_postfix()
    postfix._Postfix__ldap_search.get_user_details.return_value = []
    postfix.send_email_postfix(subject='subject', to='team-dl@redhat.com', cc=[], content='body')
    postfix._Postfix__ldap_search.get_user_details.assert_not_called()
    assert _sent_cc(mock_smtp) == ''


@patch('cloud_governance.common.mails.postfix.smtplib.SMTP')
def test_send_email_postfix_still_escalates_to_admins_for_unresolvable_username(mock_smtp):
    """
    This method tests the original safety net is preserved for a bare username that does not
    resolve in LDAP (e.g. a departed employee referenced by the User tag)
    """
    postfix = _make_postfix()
    postfix._Postfix__ldap_search.get_user_details.return_value = []
    postfix.send_email_postfix(subject='subject', to='former-employee', cc=[], content='body')
    postfix._Postfix__ldap_search.get_user_details.assert_called_once_with(user_name='former-employee')
    cc = _sent_cc(mock_smtp)
    assert 'admin1@redhat.com' in cc
    assert 'admin2@redhat.com' in cc


@patch('cloud_governance.common.mails.postfix.smtplib.SMTP')
def test_send_email_postfix_no_admin_cc_for_resolvable_username(mock_smtp):
    """
    This method tests a bare username that does resolve in LDAP is not CC'd to the default
    admins, matching today's behavior for an active employee
    """
    postfix = _make_postfix()
    postfix._Postfix__ldap_search.get_user_details.return_value = {'displayName': 'Jane Doe'}
    postfix.send_email_postfix(subject='subject', to='jdoe', cc=[], content='body')
    assert _sent_cc(mock_smtp) == ''
