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
