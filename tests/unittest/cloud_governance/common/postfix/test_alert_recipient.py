from cloud_governance.common.mails.alert_recipient import get_email_tag_value, is_valid_alert_email, \
    resolve_alert_recipient
from cloud_governance.main.environment_variables import environment_variables


def _set_allowed_domains(domains: list):
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = domains


def test_is_valid_alert_email_accepts_allowed_domain():
    """
    This method tests a well-formed address on an allowed domain is accepted
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('team-dl@redhat.com') is True


def test_is_valid_alert_email_rejects_disallowed_domain():
    """
    This method tests an address on a domain outside the allowlist is rejected
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('team-dl@gmail.com') is False


def test_is_valid_alert_email_rejects_domain_substring_bypass():
    """
    A value that merely contains the allowed domain as a substring (not as its
    actual domain) must not be treated as valid.
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('victim@redhat.com.evil.com') is False


def test_is_valid_alert_email_rejects_empty_and_na():
    """
    This method tests empty, 'NA', and None values are all rejected
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('') is False
    assert is_valid_alert_email('NA') is False
    assert is_valid_alert_email(None) is False


def test_is_valid_alert_email_rejects_header_injection():
    """
    This method tests a value containing CRLF (header-injection attempt) is rejected
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('victim@redhat.com\nBcc:attacker@evil.com') is False


def test_is_valid_alert_email_rejects_malformed_value():
    """
    This method tests a non-email-shaped value is rejected
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('not-an-email') is False


def test_is_valid_alert_email_trims_and_normalizes_case():
    """
    This method tests surrounding whitespace and domain case are normalized
    """
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email(' team-dl@RedHat.Com ') is True


def test_resolve_alert_recipient_prefers_email_tag():
    """
    This method tests a valid Email tag is preferred over the User tag
    """
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='team-dl@redhat.com', user_tag_value='jdoe') == 'team-dl@redhat.com'


def test_resolve_alert_recipient_falls_back_to_user_when_email_missing():
    """
    This method tests an empty or 'NA' Email tag falls back to the User tag
    """
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='', user_tag_value='jdoe') == 'jdoe'
    assert resolve_alert_recipient(email_tag_value='NA', user_tag_value='jdoe') == 'jdoe'


def test_resolve_alert_recipient_falls_back_to_user_when_email_invalid():
    """
    This method tests an Email tag on a disallowed domain falls back to the User tag
    """
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='team-dl@gmail.com', user_tag_value='jdoe') == 'jdoe'


def test_get_email_tag_value_matches_exact_case():
    """
    This method tests the standard 'Email' tag key is read
    """
    tags = [{'Key': 'Email', 'Value': 'team-dl@redhat.com'}]
    assert get_email_tag_value(tags=tags) == 'team-dl@redhat.com'


def test_get_email_tag_value_matches_lowercase_key():
    """
    This method tests a manually-added lowercase 'email' tag key is read
    """
    tags = [{'Key': 'email', 'Value': 'team-dl@redhat.com'}]
    assert get_email_tag_value(tags=tags) == 'team-dl@redhat.com'


def test_get_email_tag_value_matches_uppercase_key():
    """
    This method tests a manually-added uppercase 'EMAIL' tag key is read
    """
    tags = [{'Key': 'EMAIL', 'Value': 'team-dl@redhat.com'}]
    assert get_email_tag_value(tags=tags) == 'team-dl@redhat.com'


def test_get_email_tag_value_returns_empty_when_absent():
    """
    This method tests an empty string is returned when no Email tag exists
    """
    tags = [{'Key': 'User', 'Value': 'jdoe'}]
    assert get_email_tag_value(tags=tags) == ''
