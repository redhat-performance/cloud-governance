from cloud_governance.common.mails.postfix import Postfix


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
