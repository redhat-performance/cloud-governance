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
    if not email or email.upper() == 'NA' or any(ord(character) < 32 for character in email):
        return False
    if not EMAIL_REGEX.match(email):
        return False
    allowed_domains = environment_variables.environment_variables_dict.get('ALLOWED_EMAIL_DOMAINS', ['@redhat.com'])
    domain = f'@{email.rsplit("@", 1)[-1]}'.lower()
    return domain in [allowed_domain.lower() for allowed_domain in allowed_domains]


def get_email_tag_value(tags: list) -> str:
    """
    This method reads the Email tag from a resource's tags case-insensitively, so a
    manually-added 'email'/'EMAIL' key is honored the same as 'Email'. AWS tag keys are
    case-sensitive, so 'Email' and 'email' can coexist as separate tags on the same
    resource - all case-insensitive matches are scanned and the first valid address is
    returned, so a stale/invalid value on one casing doesn't hide a valid value on another.
    @param tags:
    @return:
    """
    if tags:
        for tag in tags:
            if (tag.get('Key') or '').strip().lower() == 'email':
                value = (tag.get('Value') or '').strip()
                if is_valid_alert_email(value):
                    return value
    return ''


def resolve_alert_recipient(email_tag_value: str, user_tag_value: str) -> str:
    """
    This method resolves the alert recipient for a resource, preferring the Email tag
    (self-service group/team routing) and falling back to the User tag - matching today's
    behavior when Email is unset or invalid. Returns an empty string if neither tag has a
    usable value, rather than passing through a placeholder like 'NA'.
    @param email_tag_value:
    @param user_tag_value:
    @return:
    """
    if is_valid_alert_email(email_tag_value):
        return email_tag_value.strip()
    user = (user_tag_value or '').strip()
    if user and user.upper() != 'NA':
        return user
    return ''
