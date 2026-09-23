import re

from cloud_governance.main.environment_variables import environment_variables

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def is_valid_alert_email(email: str) -> bool:
    """
    This method validates a resource's Email tag value before it is used as an alert
    recipient: well-formed, free of header-injection characters, and on an allowed domain.
    @param email:
    @return:
    """
    if not email:
        return False
    email = email.strip()
    if not email or email.upper() == 'NA' or '\n' in email or '\r' in email:
        return False
    if not EMAIL_REGEX.match(email):
        return False
    allowed_domains = environment_variables.environment_variables_dict.get('ALLOWED_EMAIL_DOMAINS', ['@redhat.com'])
    domain = f'@{email.rsplit("@", 1)[-1]}'.lower()
    return domain in [allowed_domain.lower() for allowed_domain in allowed_domains]


def resolve_alert_recipient(email_tag_value: str, user_tag_value: str) -> str:
    """
    This method resolves the alert recipient for a resource, preferring the Email tag
    (self-service group/team routing) and falling back to the User tag - matching today's
    behavior when Email is unset or invalid.
    @param email_tag_value:
    @param user_tag_value:
    @return:
    """
    if is_valid_alert_email(email_tag_value):
        return email_tag_value.strip()
    return user_tag_value
