"""
Unit tests for cloud_governance.common.jenkins.jenkins_operations.JenkinsOperations.

No network is used: the requests.Session is replaced by an in-memory fake.
"""
import base64
import json
import logging
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest
import requests

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.jenkins.jenkins_operations import (
    JenkinsOperations,
    STRING_CREDENTIAL_CLASS,
)
from cloud_governance.main.environment_variables import environment_variables

SESSION_PATH = 'cloud_governance.common.jenkins.jenkins_operations.requests.Session'
CONFIG_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl plugin="plain-credentials@143.v1b_df8b_d3b_e48">
  <scope>GLOBAL</scope>
  <id>my-cred</id>
  <description>old description</description>
  <secret>old-secret</secret>
</org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>'''


class _FakeSession:
    """Minimal stand-in for requests.Session with URL-suffix routing."""

    def __init__(self):
        self.calls = []
        self.routes = []
        self.auth = None
        self.verify = None

    def add_route(self, method: str, suffix: str, response):
        self.routes.append((method, suffix, response))

    def request(self, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        for expected_method, suffix, response in self.routes:
            if method == expected_method and url.endswith(suffix):
                return response
        raise AssertionError(f'unexpected request: {method} {url}')

    def post_calls(self):
        return [call for call in self.calls if call[0] == 'POST']


def _json_response(data, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    return response


def _invalid_json_response(status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.side_effect = ValueError('not json')
    return response


def _text_response(text: str, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


def _secret_response(secret: str):
    """Models the real /scriptText framing: 'Result: <marker><base64>\\n'."""
    payload = base64.b64encode(secret.encode('utf-8')).decode('ascii')
    return _text_response(f'Result: JENKINS_SECRET_OK:{payload}\n')


def _xml_response(content: bytes, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    return response


def _add_crumb(session: _FakeSession, status_code: int = 200, data: dict = None):
    if data is None:
        data = {'crumbRequestField': 'Jenkins-Crumb', 'crumb': 'abc123'}
    session.add_route('GET', '/crumbIssuer/api/json', _json_response(data, status_code=status_code))


@pytest.fixture
def fake_session():
    return _FakeSession()


@pytest.fixture
def make_client(fake_session):
    def _make(**kwargs):
        defaults = dict(url='https://jenkins.example.com/', username='user', api_token='token')
        defaults.update(kwargs)
        with patch(SESSION_PATH, return_value=fake_session):
            return JenkinsOperations(**defaults)
    return _make


def _post_to(session: _FakeSession, suffix: str):
    for method, url, kwargs in session.calls:
        if method == 'POST' and url.endswith(suffix):
            return url, kwargs
    raise AssertionError(f'no POST to {suffix}')


# ---------------------------------------------------------------------------
# Constructor and authentication
# ---------------------------------------------------------------------------

def test_constructor_uses_explicit_arguments(fake_session):
    with patch(SESSION_PATH, return_value=fake_session):
        JenkinsOperations(url='https://jenkins.example.com/', username='user', api_token='token')

    assert fake_session.auth == ('user', 'token')
    assert fake_session.verify is True


def test_constructor_strips_trailing_slash(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('GET', '/credentials/store/system/domain/_/api/json?depth=1',
                           _json_response({'credentials': []}))
    client = make_client(url='https://jenkins.example.com/')

    client.list_credentials()

    urls = [url for _, url, _ in fake_session.calls]
    assert 'https://jenkins.example.com/credentials/store/system/domain/_/api/json?depth=1' in urls


def test_constructor_falls_back_to_environment_variables(monkeypatch, fake_session):
    monkeypatch.setitem(environment_variables.environment_variables_dict, 'JENKINS_URL', 'https://env.example.com/')
    monkeypatch.setitem(environment_variables.environment_variables_dict, 'JENKINS_USERNAME', 'env-user')
    monkeypatch.setitem(environment_variables.environment_variables_dict, 'JENKINS_API_TOKEN', 'env-token')
    monkeypatch.setitem(environment_variables.environment_variables_dict, 'JENKINS_PASSWORD', '')
    monkeypatch.setitem(environment_variables.environment_variables_dict, 'JENKINS_VERIFY_SSL', False)

    with patch(SESSION_PATH, return_value=fake_session):
        JenkinsOperations()

    assert fake_session.auth == ('env-user', 'env-token')
    assert fake_session.verify is False


def test_constructor_prefers_api_token_over_password(fake_session):
    with patch(SESSION_PATH, return_value=fake_session):
        JenkinsOperations(url='https://jenkins.example.com/', username='user',
                          api_token='token', password='password')

    assert fake_session.auth == ('user', 'token')


def test_constructor_supports_password_only(fake_session):
    with patch(SESSION_PATH, return_value=fake_session):
        JenkinsOperations(url='https://jenkins.example.com/', username='user',
                          api_token='', password='password')

    assert fake_session.auth == ('user', 'password')


def test_constructor_without_credentials_leaves_auth_unset(fake_session):
    with patch(SESSION_PATH, return_value=fake_session):
        JenkinsOperations(url='https://jenkins.example.com/', username='user', api_token='', password='')

    assert fake_session.auth is None


def test_request_requires_configuration(fake_session):
    with patch(SESSION_PATH, return_value=fake_session):
        client = JenkinsOperations(url='', username='user', api_token='token')

    with pytest.raises(JenkinsOperationsError) as error:
        client.list_credentials()

    assert 'must be configured' in str(error.value)
    assert fake_session.calls == []


# ---------------------------------------------------------------------------
# read_bound_secret
# ---------------------------------------------------------------------------

def test_read_bound_secret_reads_environment(monkeypatch, make_client, fake_session):
    monkeypatch.setenv('BOUND_SECRET', 'bound-value')
    client = make_client()

    assert client.read_bound_secret('BOUND_SECRET') == 'bound-value'
    assert fake_session.calls == []


def test_read_bound_secret_raises_for_missing_variable(monkeypatch, make_client):
    monkeypatch.delenv('MISSING_SECRET', raising=False)
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_bound_secret('MISSING_SECRET')

    assert "'MISSING_SECRET'" in str(error.value)
    assert 'bound-value' not in str(error.value)


def test_read_bound_secret_works_without_jenkins_configuration(monkeypatch, fake_session):
    monkeypatch.setenv('BOUND_SECRET', 'bound-value')
    with patch(SESSION_PATH, return_value=fake_session):
        client = JenkinsOperations(url='', username='', api_token='', password='')

    assert client.read_bound_secret('BOUND_SECRET') == 'bound-value'


# ---------------------------------------------------------------------------
# read_secret (admin Script Console)
# ---------------------------------------------------------------------------

def test_read_secret_requires_script_console_opt_in(make_client, fake_session):
    client = make_client(allow_script_console=False)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'allow_script_console' in str(error.value)
    assert fake_session.calls == []


def test_read_secret_posts_groovy_and_returns_value_verbatim(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _secret_response('  secret-with-spaces  '))
    client = make_client(allow_script_console=True)

    assert client.read_secret('my-cred') == '  secret-with-spaces  '

    _, kwargs = _post_to(fake_session, '/scriptText')
    script = kwargs['data']['script']
    assert 'it.id == "my-cred"' in script
    assert 'CredentialsProvider.lookupCredentials' in script
    assert 'it.class.name.endsWith("StringCredentialsImpl")' in script
    assert 'com.cloudbees.plugins.credentials.impl.StringCredentialsImpl' not in script
    assert 'JENKINS_SECRET_OK' in script
    assert 'encodeBase64' in script
    assert kwargs['headers']['Jenkins-Crumb'] == 'abc123'


def test_read_secret_unwraps_the_result_prefix(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _secret_response('value'))
    client = make_client(allow_script_console=True)

    assert client.read_secret('my-cred') == 'value'


def test_read_secret_escapes_credentials_id_in_groovy(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _secret_response('value'))
    client = make_client(allow_script_console=True)
    credentials_id = 'id"with\\backslash\nnewline'

    client.read_secret(credentials_id)

    _, kwargs = _post_to(fake_session, '/scriptText')
    assert f'it.id == {json.dumps(credentials_id)}' in kwargs['data']['script']


def test_read_secret_escapes_groovy_interpolation(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _secret_response('value'))
    client = make_client(allow_script_console=True)

    client.read_secret('price$and${7*7}')

    _, kwargs = _post_to(fake_session, '/scriptText')
    script = kwargs['data']['script']
    assert r'"price\$and\${7*7}"' in script
    assert r'\${7*7}' in script


def test_read_secret_raises_when_credential_is_missing(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response(''))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'was not found' in str(error.value)


def test_read_secret_raises_on_script_error_sentinel(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route(
        'POST', '/scriptText',
        _text_response('Result: JENKINS_SECRET_READ_ERROR:groovy.lang.MissingMethodException\n'))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    message = str(error.value)
    assert 'could not read the credential' in message
    assert 'groovy.lang.MissingMethodException' in message
    assert 'my-cred' not in message


def test_read_secret_raises_on_not_found_sentinel(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText',
                           _text_response('Result: JENKINS_SECRET_READ_ERROR:not-found\n'))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'was not found' in str(error.value)


def test_read_secret_rejects_raw_groovy_stack_trace(make_client, fake_session):
    _add_crumb(fake_session)
    stack_trace = (
        'groovy.lang.MissingPropertyException: No such property: x\n'
        '\tat org.codehaus.groovy.runtime.ScriptBytecodeAdapter.unwrap(ScriptBytecodeAdapter.java:50)'
    )
    fake_session.add_route('POST', '/scriptText', _text_response(stack_trace))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'returned an error instead of the secret' in str(error.value)
    assert 'my-cred' not in str(error.value)


def test_read_secret_rejects_invalid_base64_payload(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText',
                           _text_response('Result: JENKINS_SECRET_OK:not-base64!\n'))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'invalid secret payload' in str(error.value)
    assert 'my-cred' not in str(error.value)


def test_read_secret_rejects_unrecognized_body(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response('Result: something unexpected\n'))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert 'unrecognized response' in str(error.value)


def test_read_secret_script_catches_and_reports_failures(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _secret_response('value'))
    client = make_client(allow_script_console=True)

    client.read_secret('my-cred')

    _, kwargs = _post_to(fake_session, '/scriptText')
    script = kwargs['data']['script']
    assert 'try {' in script
    assert 'catch (Throwable throwable)' in script
    assert 'JENKINS_SECRET_READ_ERROR' in script


def test_read_secret_sanitizes_403(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response('', status_code=403))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert error.value.status_code == 403
    assert 'Overall/Administer' in str(error.value)
    assert 'my-cred' not in str(error.value)
    assert 'token' not in str(error.value)


def test_read_secret_sanitizes_401(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response('denied', status_code=401))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    message = str(error.value)
    assert 'HTTP 401' in message
    assert 'JENKINS_USERNAME' in message
    assert 'JENKINS_API_TOKEN' in message
    assert 'rejected the API token' in message
    assert error.value.status_code == 401
    assert 'my-cred' not in message


def test_401_message_names_the_password_when_no_token_is_configured(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response('denied', status_code=401))
    client = make_client(allow_script_console=True, api_token='', password='secret')

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    message = str(error.value)
    assert 'rejected the password' in message
    assert 'secret' not in message


def test_read_secret_sanitizes_500(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/scriptText', _text_response('server exploded', status_code=500))
    client = make_client(allow_script_console=True)

    with pytest.raises(JenkinsOperationsError) as error:
        client.read_secret('my-cred')

    assert str(error.value) == 'Jenkins request failed with HTTP 500'
    assert error.value.status_code == 500


# ---------------------------------------------------------------------------
# CSRF crumbs
# ---------------------------------------------------------------------------

def test_post_adds_csrf_crumb(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/createCredentials', _json_response({}))
    client = make_client()

    client.create_secret('my-cred', 's3cret')

    _, kwargs = _post_to(fake_session, '/createCredentials')
    assert kwargs['headers']['Jenkins-Crumb'] == 'abc123'


@pytest.mark.parametrize('status_code', [403, 404])
def test_post_works_when_crumb_endpoint_is_disabled(make_client, fake_session, status_code):
    _add_crumb(fake_session, status_code=status_code, data={})
    fake_session.add_route('POST', '/createCredentials', _json_response({}))
    client = make_client()

    client.create_secret('my-cred', 's3cret')

    _, kwargs = _post_to(fake_session, '/createCredentials')
    assert 'Jenkins-Crumb' not in kwargs['headers']


def test_post_raises_on_invalid_crumb_response(make_client, fake_session):
    _add_crumb(fake_session, data={'unexpected': 'shape'})
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.create_secret('my-cred', 's3cret')

    assert 'invalid response' in str(error.value)
    assert 'my-cred' not in str(error.value)
    assert 's3cret' not in str(error.value)


# ---------------------------------------------------------------------------
# create_secret
# ---------------------------------------------------------------------------

def test_create_secret_posts_expected_payload(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/createCredentials', _json_response({}, status_code=200))
    client = make_client()

    client.create_secret('my-cred', 's3cret', description='a description')

    _, kwargs = _post_to(fake_session, '/createCredentials')
    assert json.loads(kwargs['data']['json']) == {
        '': '0',
        'credentials': {
            'scope': 'GLOBAL',
            'id': 'my-cred',
            'description': 'a description',
            'secret': 's3cret',
            '$class': STRING_CREDENTIAL_CLASS,
        },
    }


def test_create_secret_uses_plain_credentials_class(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/createCredentials', _json_response({}, status_code=200))
    client = make_client()

    client.create_secret('my-cred', 's3cret')

    _, kwargs = _post_to(fake_session, '/createCredentials')
    payload = json.loads(kwargs['data']['json'])
    assert payload['credentials']['$class'] == (
        'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl')


@pytest.mark.parametrize('credentials_id,secret', [('', 's3cret'), ('my-cred', '')])
def test_create_secret_rejects_empty_inputs(make_client, fake_session, credentials_id, secret):
    client = make_client()

    with pytest.raises(JenkinsOperationsError):
        client.create_secret(credentials_id, secret)

    assert fake_session.calls == []


def test_create_secret_sanitizes_http_error(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/createCredentials', _json_response({}, status_code=500))
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.create_secret('my-cred', 's3cret')

    assert str(error.value) == 'Jenkins request failed with HTTP 500'
    assert 'my-cred' not in str(error.value)
    assert 's3cret' not in str(error.value)


def test_create_secret_logs_event_without_sensitive_values(make_client, fake_session, caplog):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/createCredentials', _json_response({}))
    client = make_client()

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        client.create_secret('my-cred', 's3cret', description='description')

    assert 'Created the Jenkins credential' in caplog.text
    assert 'my-cred' not in caplog.text
    assert 's3cret' not in caplog.text
    assert 'token' not in caplog.text


# ---------------------------------------------------------------------------
# update_secret
# ---------------------------------------------------------------------------

def _prepare_update(fake_session, config_xml: bytes = CONFIG_XML, get_status: int = 200,
                    post_status: int = 200):
    _add_crumb(fake_session)
    fake_session.add_route('GET', '/credential/my-cred/config.xml',
                           _xml_response(config_xml, status_code=get_status))
    fake_session.add_route('POST', '/credential/my-cred/config.xml',
                           _json_response({}, status_code=post_status))


def test_update_secret_replaces_secret_and_preserves_metadata(make_client, fake_session):
    _prepare_update(fake_session)
    client = make_client()

    client.update_secret('my-cred', 'new-secret')

    _, kwargs = _post_to(fake_session, '/credential/my-cred/config.xml')
    posted = ET.fromstring(kwargs['data'])
    assert posted.findtext('secret') == 'new-secret'
    assert posted.findtext('id') == 'my-cred'
    assert posted.findtext('scope') == 'GLOBAL'
    assert posted.findtext('description') == 'old description'
    assert kwargs['headers']['Content-Type'] == 'application/xml'


def test_update_secret_replaces_description_when_given(make_client, fake_session):
    _prepare_update(fake_session)
    client = make_client()

    client.update_secret('my-cred', 'new-secret', description='new description')

    _, kwargs = _post_to(fake_session, '/credential/my-cred/config.xml')
    assert ET.fromstring(kwargs['data']).findtext('description') == 'new description'


def test_update_secret_creates_missing_secret_element(make_client, fake_session):
    xml_without_secret = b'''<org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>
  <scope>GLOBAL</scope>
  <id>my-cred</id>
</org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>'''
    _prepare_update(fake_session, config_xml=xml_without_secret)
    client = make_client()

    client.update_secret('my-cred', 'new-secret')

    _, kwargs = _post_to(fake_session, '/credential/my-cred/config.xml')
    assert ET.fromstring(kwargs['data']).findtext('secret') == 'new-secret'


def test_update_secret_raises_when_credential_is_missing(make_client, fake_session):
    _prepare_update(fake_session, get_status=404)
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.update_secret('my-cred', 'new-secret')

    assert error.value.status_code == 404
    assert 'was not found' in str(error.value)


def test_update_secret_sanitizes_malformed_xml(make_client, fake_session):
    _prepare_update(fake_session, config_xml=b'<not-xml')
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.update_secret('my-cred', 'new-secret')

    assert 'could not be parsed' in str(error.value)
    assert 'my-cred' not in str(error.value)


def test_update_secret_rejects_non_secret_text_credential(make_client, fake_session):
    username_password_xml = b'''<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
  <scope>GLOBAL</scope>
  <id>my-cred</id>
  <username>user</username>
  <password>pass</password>
</com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>'''
    _prepare_update(fake_session, config_xml=username_password_xml)
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.update_secret('my-cred', 'new-secret')

    assert 'not a secret text credential' in str(error.value)
    assert 'my-cred' not in str(error.value)
    assert not [call for call in fake_session.post_calls()
                if str(call[1]).endswith('/config.xml')]


def test_update_secret_logs_event_without_sensitive_values(make_client, fake_session, caplog):
    _prepare_update(fake_session)
    client = make_client()

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        client.update_secret('my-cred', 'new-secret')

    assert 'Updated the Jenkins credential' in caplog.text
    assert 'my-cred' not in caplog.text
    assert 'new-secret' not in caplog.text


# ---------------------------------------------------------------------------
# delete_secret
# ---------------------------------------------------------------------------

def test_delete_secret_returns_true_on_success(make_client, fake_session, caplog):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/credential/my-cred/doDelete', _json_response({}))
    client = make_client()

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        assert client.delete_secret('my-cred') is True

    assert 'Deleted the Jenkins credential' in caplog.text
    assert 'my-cred' not in caplog.text


def test_delete_secret_returns_false_on_404(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/credential/my-cred/doDelete', _json_response({}, status_code=404))
    client = make_client()

    assert client.delete_secret('my-cred') is False


def test_delete_secret_sanitizes_500(make_client, fake_session):
    _add_crumb(fake_session)
    fake_session.add_route('POST', '/credential/my-cred/doDelete', _json_response({}, status_code=500))
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.delete_secret('my-cred')

    assert str(error.value) == 'Jenkins request failed with HTTP 500'


# ---------------------------------------------------------------------------
# Metadata: exists / get / list
# ---------------------------------------------------------------------------

def test_credential_exists_true_and_false(make_client, fake_session):
    client = make_client()
    fake_session.add_route('GET', '/credential/my-cred/api/json', _json_response({'id': 'my-cred'}))

    assert client.credential_exists('my-cred') is True

    fake_session.routes.clear()
    fake_session.add_route('GET', '/credential/my-cred/api/json', _json_response({}, status_code=404))

    assert client.credential_exists('my-cred') is False


def test_get_credential_returns_metadata_and_none(make_client, fake_session):
    client = make_client()
    fake_session.add_route('GET', '/credential/my-cred/api/json',
                           _json_response({'id': 'my-cred', 'description': 'desc'}))

    assert client.get_credential('my-cred') == {'id': 'my-cred', 'description': 'desc'}

    fake_session.routes.clear()
    fake_session.add_route('GET', '/credential/my-cred/api/json', _json_response({}, status_code=404))

    assert client.get_credential('my-cred') is None


def test_get_credential_raises_on_invalid_json(make_client, fake_session):
    fake_session.add_route('GET', '/credential/my-cred/api/json', _invalid_json_response())
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.get_credential('my-cred')

    assert 'invalid JSON' in str(error.value)


def test_list_credentials_returns_list(make_client, fake_session):
    fake_session.add_route('GET', '/credentials/store/system/domain/_/api/json?depth=1',
                           _json_response({'credentials': [{'id': 'one'}, {'id': 'two'}]}))
    client = make_client()

    assert client.list_credentials() == [{'id': 'one'}, {'id': 'two'}]


def test_list_credentials_handles_missing_key(make_client, fake_session):
    fake_session.add_route('GET', '/credentials/store/system/domain/_/api/json?depth=1', _json_response({}))
    client = make_client()

    assert client.list_credentials() == []


def test_list_credentials_raises_when_credentials_is_not_a_list(make_client, fake_session):
    fake_session.add_route('GET', '/credentials/store/system/domain/_/api/json?depth=1',
                           _json_response({'credentials': 'unexpected'}))
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.list_credentials()

    assert 'invalid JSON' in str(error.value)


def test_credential_ids_are_percent_encoded(make_client, fake_session):
    fake_session.add_route('GET', '/credential/team%2Fa%20b/api/json', _json_response({}, status_code=404))
    client = make_client()

    client.credential_exists('team/a b')

    assert fake_session.calls[-1][1].endswith('/credential/team%2Fa%20b/api/json')


# ---------------------------------------------------------------------------
# write_secret
# ---------------------------------------------------------------------------

def test_write_secret_creates_when_missing(make_client, monkeypatch):
    client = make_client()
    calls = []
    monkeypatch.setattr(client, 'credential_exists', lambda credentials_id: False)
    monkeypatch.setattr(client, 'create_secret',
                        lambda credentials_id, secret, description='':
                        calls.append(('create', credentials_id, secret, description)))
    monkeypatch.setattr(client, 'update_secret', lambda *args, **kwargs: calls.append(('update',)))

    assert client.write_secret('my-cred', 's3cret') == 'created'
    assert calls == [('create', 'my-cred', 's3cret', '')]


def test_write_secret_updates_when_present(make_client, monkeypatch):
    client = make_client()
    calls = []
    monkeypatch.setattr(client, 'credential_exists', lambda credentials_id: True)
    monkeypatch.setattr(client, 'create_secret', lambda *args, **kwargs: calls.append(('create',)))
    monkeypatch.setattr(client, 'update_secret',
                        lambda credentials_id, secret, description=None:
                        calls.append(('update', credentials_id, secret, description)))

    assert client.write_secret('my-cred', 's3cret') == 'updated'
    assert calls == [('update', 'my-cred', 's3cret', None)]


def test_write_secret_passes_description_on_update(make_client, monkeypatch):
    client = make_client()
    calls = []
    monkeypatch.setattr(client, 'credential_exists', lambda credentials_id: True)
    monkeypatch.setattr(client, 'update_secret',
                        lambda credentials_id, secret, description=None:
                        calls.append(('update', credentials_id, secret, description)))

    client.write_secret('my-cred', 's3cret', description='new description')

    assert calls == [('update', 'my-cred', 's3cret', 'new description')]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def test_request_exception_does_not_leak_url_or_credential_id(make_client, fake_session):
    def explode(method, url, **kwargs):
        raise requests.ConnectionError(f'failed for {url}')

    fake_session.request = explode
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.credential_exists('my-cred')

    assert 'ConnectionError' in str(error.value)
    assert 'my-cred' not in str(error.value)
    assert 'token' not in str(error.value)


def test_ssl_error_explains_how_to_fix_verification(make_client, fake_session):
    def explode(method, url, **kwargs):
        raise requests.exceptions.SSLError(f'certificate verify failed for {url}')

    fake_session.request = explode
    client = make_client()

    with pytest.raises(JenkinsOperationsError) as error:
        client.credential_exists('my-cred')

    message = str(error.value)
    assert 'TLS certificate verification failed' in message
    assert 'REQUESTS_CA_BUNDLE' in message
    assert 'JENKINS_VERIFY_SSL=false' in message
    assert 'https://jenkins.example.com' not in message
    assert 'my-cred' not in message


def test_lifecycle_logs_no_sensitive_values(make_client, fake_session, caplog):
    _prepare_update(fake_session)
    fake_session.add_route('POST', '/credential/my-cred/doDelete', _json_response({}))
    client = make_client()

    with caplog.at_level(logging.INFO, logger='cloud_governance'):
        client.update_secret('my-cred', 'new-secret')
        client.delete_secret('my-cred')

    for forbidden in ('my-cred', 'new-secret', 'old-secret', 'token', 'user'):
        assert forbidden not in caplog.text
