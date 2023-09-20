from typing import Union

from cloud_governance.main.environment_variables import environment_variables


def string_equal_ignore_case(value1: str, value2: str, *args) -> bool:
    """
    This method finds all values are equal and returns bool
    :return:
    """
    equal = value1.lower() == value2.lower()
    if args:
        for val in args:
            equal = value1.lower() == val.lower() and equal
    return equal


def integer_equal(value1: int, value2: int, *args) -> bool:
    """
    This method finds all values are equal and returns bool
    :param value1:
    :param value2:
    :param args:
    :return:
    """
    equal = value1 == value2
    if args:
        for val in args:
            equal = equal and value1 == val
    return equal


def get_tag_value_by_name(tags: list, tag_name: str) -> str:
    """
    This method returns the tag_value
    :param tags:
    :param tag_name:
    :return:
    """
    for tag in tags:
        key = tag.get('Key')
        value = tag.get('Value')
        if string_equal_ignore_case(key, tag_name):
            return value
    return ''


def get_ldap_user_data(user: str, tag_name: str):
    """
    This method returns the ldap user tag_name
    :param user:
    :param tag_name:
    :return:
    """
    from cloud_governance.common.ldap.ldap_search import LdapSearch
    ldap_search = LdapSearch(ldap_host_name=environment_variables.environment_variables_dict.get('LDAP_HOST_NAME', ''))
    user_details = ldap_search.get_user_details(user)
    if user_details:
        return user_details.get(tag_name)
    return 'NA'


def check_name_and_get_key_from_tags(tags: Union[list, dict], tag_name: str, default: str = '', replace_spl: bool = False) -> [str, str]:
    """
    This method returns the key and value if tag_name present in the key
    :param replace_spl:
    :type replace_spl:
    :param default:
    :type default:
    :param tags:
    :type tags:
    :param tag_name:
    :type tag_name:
    :return:
    :rtype:
    """
    if tags:
        if type(tags) == list:
            tags = {tag.get('Key'): tag.get('Value') for tag in tags}
        for key, value in tags.items():
            if replace_spl:
                key = key.lower().replace("_", '').replace("-", '').strip()
            else:
                key = key.lower().strip()
            if tag_name.lower() in key:
                return key, value
    return default, default
