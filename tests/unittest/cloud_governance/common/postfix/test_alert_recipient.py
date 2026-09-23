from cloud_governance.common.mails.alert_recipient import is_valid_alert_email, resolve_alert_recipient
from cloud_governance.main.environment_variables import environment_variables


def _set_allowed_domains(domains: list):
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = domains


def test_is_valid_alert_email_accepts_allowed_domain():
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('team-dl@redhat.com') is True


def test_is_valid_alert_email_rejects_disallowed_domain():
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
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('') is False
    assert is_valid_alert_email('NA') is False
    assert is_valid_alert_email(None) is False


def test_is_valid_alert_email_rejects_header_injection():
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('victim@redhat.com\nBcc:attacker@evil.com') is False


def test_is_valid_alert_email_rejects_malformed_value():
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email('not-an-email') is False


def test_is_valid_alert_email_trims_and_normalizes_case():
    _set_allowed_domains(['@redhat.com'])
    assert is_valid_alert_email(' team-dl@RedHat.Com ') is True


def test_resolve_alert_recipient_prefers_email_tag():
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='team-dl@redhat.com', user_tag_value='jdoe') == 'team-dl@redhat.com'


def test_resolve_alert_recipient_falls_back_to_user_when_email_missing():
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='', user_tag_value='jdoe') == 'jdoe'
    assert resolve_alert_recipient(email_tag_value='NA', user_tag_value='jdoe') == 'jdoe'


def test_resolve_alert_recipient_falls_back_to_user_when_email_invalid():
    _set_allowed_domains(['@redhat.com'])
    assert resolve_alert_recipient(email_tag_value='team-dl@gmail.com', user_tag_value='jdoe') == 'jdoe'
