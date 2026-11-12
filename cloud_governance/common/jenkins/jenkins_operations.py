"""
Jenkins credential operations for cloud-governance.

Jenkins never returns a credential value through its ordinary REST API. There are two ways to
read a secret:

1. A pipeline binds the credential to an environment variable with
   ``environment { VAR = credentials('id') }`` or ``withCredentials([...])``.
   The process then reads it from ``os.environ`` -- see ``read_bound_secret``. This is the
   normal, non-admin path and is what the cloud-governance Jenkinsfiles already do.
2. The Script Console (``POST /scriptText``) can resolve the plaintext value. It requires an
   account with Overall/Administer and is therefore opt-in via ``allow_script_console=True``.

Writing does not need the Script Console: the credentials plugin exposes ``createCredentials``,
``config.xml`` and ``doDelete`` under ``/credentials/store/system/domain/_``.

Authentication supports either a username + API token or a username + password (Jenkins HTTP
basic auth accepts both). The API token is preferred when both are configured.

Secrets, tokens, passwords, usernames and credential ids must never be logged or included in
exception messages.
"""
import base64
import binascii
import json
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from cloud_governance.common.jenkins.jenkins_exceptions import JenkinsOperationsError
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables

CREDENTIALS_STORE_PATH = '/credentials/store/system/domain/_'
# "Secret text" is provided by the plain-credentials plugin. The credentials plugin itself does
# not contain StringCredentialsImpl; importing that name fails to compile in the Script Console.
STRING_CREDENTIAL_CLASS = 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl'
STRING_CREDENTIAL_CLASS_SUFFIX = 'StringCredentialsImpl'
# The Script Console answers HTTP 200 even when the Groovy throws and returns the stack trace as
# the body. It also wraps successful results as 'Result: <value>\n'. The script therefore returns
# a base64 payload behind a marker, which Python can extract regardless of that wrapper, and
# reports its own failures with an error marker so they can never be mistaken for a secret.
SECRET_OK_PREFIX = 'JENKINS_SECRET_OK:'
SECRET_ERROR_PREFIX = 'JENKINS_SECRET_READ_ERROR:'
STACK_TRACE_EXCEPTION_PATTERN = re.compile(
    r'^(?:[A-Za-z_$][\w$]*\.)+[A-Za-z_$][\w$]*(?:Exception|Error|Throwable)\b')


class JenkinsOperations:
    """
    Client for reading and writing Jenkins credentials.
    """

    def __init__(self, url: str = None, username: str = None, api_token: str = None,
                 password: str = None, verify_ssl: bool = None, allow_script_console: bool = False,
                 timeout: int = 30):
        """
        :param url: Jenkins base URL. Defaults to JENKINS_URL.
        :param username: Jenkins user. Defaults to JENKINS_USERNAME.
        :param api_token: Jenkins API token. Defaults to JENKINS_API_TOKEN.
        :param password: Jenkins password, used only when no API token is configured.
            Defaults to JENKINS_PASSWORD.
        :param verify_ssl: Verify the TLS certificate. Defaults to JENKINS_VERIFY_SSL (true).
        :param allow_script_console: Enable read_secret through POST /scriptText. Requires an
            account with Overall/Administer.
        :param timeout: HTTP timeout in seconds.
        """
        env = environment_variables.environment_variables_dict
        self.__url = (url if url is not None else env.get('JENKINS_URL') or '').strip().rstrip('/')
        self.__username = (username if username is not None else env.get('JENKINS_USERNAME') or '').strip()
        self.__api_token = (api_token if api_token is not None else env.get('JENKINS_API_TOKEN') or '').strip()
        self.__password = (password if password is not None else env.get('JENKINS_PASSWORD') or '').strip()
        if verify_ssl is None:
            verify_ssl = env.get('JENKINS_VERIFY_SSL', True)
        self.__verify_ssl = verify_ssl
        self.__allow_script_console = allow_script_console
        self.__timeout = timeout
        self.__session = requests.Session()
        self.__session.verify = self.__verify_ssl
        auth_secret = self.__api_token or self.__password
        if self.__username and auth_secret:
            self.__session.auth = (self.__username, auth_secret)

    @property
    def allow_script_console(self) -> bool:
        return self.__allow_script_console

    @staticmethod
    def __validate_credentials_id(credentials_id: str):
        if not isinstance(credentials_id, str) or not credentials_id.strip():
            raise JenkinsOperationsError('Jenkins credential id must be a non-empty string')

    @staticmethod
    def __validate_secret(secret: str):
        if not isinstance(secret, str) or secret == '':
            raise JenkinsOperationsError('Jenkins secret must be a non-empty string')

    @staticmethod
    def __credential_path(credentials_id: str) -> str:
        """
        Builds the REST path of a single credential. quote(..., safe='') encodes '/' and spaces,
        so an id can never escape the credentials domain.
        """
        return f'{CREDENTIALS_STORE_PATH}/credential/{quote(credentials_id, safe="")}'

    @staticmethod
    def __parse_json_object(response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise JenkinsOperationsError('Jenkins returned an invalid JSON response') from None
        if not isinstance(data, dict):
            raise JenkinsOperationsError('Jenkins returned an invalid JSON response')
        return data

    def __request(self, method: str, path: str, expected_statuses: tuple = (200,), **kwargs):
        """
        Sends one HTTP request. Errors are deliberately sanitized: requests exceptions embed the
        URL, which contains the credential id, and response bodies can echo scripts. Only the
        HTTP status code is reported.
        """
        if not (self.__url and self.__username and (self.__api_token or self.__password)):
            raise JenkinsOperationsError(
                'Jenkins URL, username and an API token or password must be configured')
        url = f'{self.__url}{path}'
        try:
            response = self.__session.request(method, url, timeout=self.__timeout, **kwargs)
        except requests.exceptions.SSLError:
            # Never verified: the TLS handshake fails before any credential is sent. The URL
            # stays out of the message; the hint is what actually fixes it.
            raise JenkinsOperationsError(
                'Jenkins TLS certificate verification failed; trust the Jenkins CA with '
                'REQUESTS_CA_BUNDLE, or set JENKINS_VERIFY_SSL=false for a self-signed '
                'certificate') from None
        except requests.RequestException as err:
            raise JenkinsOperationsError(f'Jenkins request failed: {type(err).__name__}') from None
        if response.status_code not in expected_statuses:
            if response.status_code == 401:
                # Name the rejected auth form: it is never sensitive, and it tells a caller with
                # both configured that a stale JENKINS_API_TOKEN took precedence over the password.
                auth_method = 'API token' if self.__api_token else 'password'
                raise JenkinsOperationsError(
                    f'Jenkins rejected the {auth_method} with HTTP 401; check JENKINS_USERNAME and '
                    'JENKINS_API_TOKEN or JENKINS_PASSWORD, and that the token was not revoked',
                    status_code=401)
            raise JenkinsOperationsError(
                f'Jenkins request failed with HTTP {response.status_code}',
                status_code=response.status_code)
        return response

    def __get_csrf_headers(self) -> dict:
        """
        Jenkins requires a CSRF crumb on mutating requests when the crumbs are enabled. When they
        are disabled the endpoint answers 404 (or 403 for anonymous access); in that case no
        crumb header is needed.
        """
        response = self.__request('GET', '/crumbIssuer/api/json', expected_statuses=(200, 403, 404))
        if response.status_code != 200:
            return {}
        try:
            data = response.json()
        except ValueError:
            raise JenkinsOperationsError('Jenkins crumb issuer returned an invalid response') from None
        if not isinstance(data, dict) or not data.get('crumbRequestField') or not data.get('crumb'):
            raise JenkinsOperationsError('Jenkins crumb issuer returned an invalid response')
        return {data['crumbRequestField']: data['crumb']}

    def __post(self, path: str, expected_statuses: tuple = (200,), **kwargs):
        headers = dict(kwargs.pop('headers', None) or {})
        headers.update(self.__get_csrf_headers())
        return self.__request('POST', path, expected_statuses=expected_statuses, headers=headers, **kwargs)

    @staticmethod
    def __build_secret_script(credentials_id: str) -> str:
        """
        Builds the Script Console Groovy. json.dumps produces a valid Groovy double-quoted string
        literal (escaping quotes, backslashes and control characters), so the id cannot break out
        of the literal.
        """
        # json.dumps escapes quotes, backslashes and control characters, but Groovy still
        # interpolates ${...} inside a double-quoted GString, so '$' must be escaped as well.
        # The id is caller-controlled; without this it would run arbitrary Groovy as admin.
        id_literal = json.dumps(credentials_id).replace('$', '\\$')
        return (
            'import com.cloudbees.plugins.credentials.CredentialsProvider\n'
            'import com.cloudbees.plugins.credentials.Credentials\n'
            'try {\n'
            '    def matches = CredentialsProvider.lookupCredentials(\n'
            '        Credentials.class,\n'
            '        jenkins.model.Jenkins.instance,\n'
            '        null,\n'
            '        null\n'
            '    ).findAll {\n'
            '        it.id == ' + id_literal + ' &&\n'
            '            it.class.name.endsWith(' + json.dumps(STRING_CREDENTIAL_CLASS_SUFFIX) + ')\n'
            '    }\n'
            '    if (matches.size() != 1) {\n'
            '        return ' + json.dumps(SECRET_ERROR_PREFIX + 'not-found') + '\n'
            '    }\n'
            '    return ' + json.dumps(SECRET_OK_PREFIX) +
            ' + matches[0].secret.plainText.getBytes("UTF-8").encodeBase64().toString()\n'
            '} catch (Throwable throwable) {\n'
            '    return ' + json.dumps(SECRET_ERROR_PREFIX) + ' + throwable.class.name\n'
            '}\n'
        )

    @staticmethod
    def __extract_marker_payload(body: str, prefix: str) -> str:
        """
        Returns the token that follows the marker up to the next whitespace, or None when the
        marker is absent. The Script Console wraps results as 'Result: <value>\\n', so the marker
        is not at the start of the body.
        """
        index = body.find(prefix)
        if index == -1:
            return None
        remainder = body[index + len(prefix):]
        for position, character in enumerate(remainder):
            if character.isspace():
                return remainder[:position]
        return remainder

    @staticmethod
    def __decode_secret_payload(payload: str) -> str:
        try:
            return base64.b64decode(payload, validate=True).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            raise JenkinsOperationsError('Jenkins returned an invalid secret payload') from None

    @staticmethod
    def __looks_like_stack_trace(text: str) -> bool:
        """
        The Script Console can return the raw Groovy stack trace with HTTP 200, for example when
        the failure happens before the script's try block. Its first line is
        '<qualified.ExceptionClass>: <message>' followed by '\tat ...' frames.
        """
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2 or not lines[1].lstrip().startswith('at '):
            return False
        return STACK_TRACE_EXCEPTION_PATTERN.match(lines[0].strip()) is not None

    def read_bound_secret(self, variable: str) -> str:
        """
        Reads a credential that a Jenkins pipeline bound to an environment variable with
        ``credentials()`` or ``withCredentials()``. This performs no HTTP call and needs no
        Jenkins permissions.
        :param variable: Environment variable name, e.g. 'AWS_SECRET_ACCESS_KEY'.
        :return: The secret value.
        """
        if not isinstance(variable, str) or not variable.strip():
            raise JenkinsOperationsError('Environment variable name must be a non-empty string')
        value = os.environ.get(variable)
        if value is None or value == '':
            raise JenkinsOperationsError(
                f'Environment variable {variable!r} is not set; '
                f'bind the credential with credentials() in the pipeline')
        return value

    def read_secret(self, credentials_id: str) -> str:
        """
        Reads a secret-text credential value through the Script Console.
        Requires allow_script_console=True and an account with Overall/Administer.
        :param credentials_id: Jenkins credential id.
        :return: The plaintext secret, verbatim.
        """
        self.__validate_credentials_id(credentials_id)
        if not self.__allow_script_console:
            raise JenkinsOperationsError(
                'read_secret requires allow_script_console=True and a Jenkins account '
                'with Overall/Administer')
        response = self.__post('/scriptText', expected_statuses=(200, 403),
                               data={'script': self.__build_secret_script(credentials_id)})
        if response.status_code == 403:
            raise JenkinsOperationsError(
                'Jenkins denied /scriptText with HTTP 403; read_secret requires Overall/Administer',
                status_code=403)
        body = response.text
        error_payload = self.__extract_marker_payload(body, SECRET_ERROR_PREFIX)
        if error_payload is not None:
            reason = error_payload or 'unknown error'
            if reason == 'not-found':
                raise JenkinsOperationsError('Jenkins credential was not found')
            raise JenkinsOperationsError(f'Jenkins could not read the credential ({reason})')
        success_payload = self.__extract_marker_payload(body, SECRET_OK_PREFIX)
        if success_payload is not None:
            return self.__decode_secret_payload(success_payload)
        if body.strip() == '':
            raise JenkinsOperationsError('Jenkins credential was not found')
        if self.__looks_like_stack_trace(body):
            raise JenkinsOperationsError(
                'Jenkins script console returned an error instead of the secret')
        raise JenkinsOperationsError(
            'Jenkins returned an unrecognized response instead of the secret')

    def credential_exists(self, credentials_id: str) -> bool:
        """
        :return: True when the credential exists, False on HTTP 404.
        """
        self.__validate_credentials_id(credentials_id)
        response = self.__request('GET', f'{self.__credential_path(credentials_id)}/api/json',
                                  expected_statuses=(200, 404))
        return response.status_code == 200

    def get_credential(self, credentials_id: str) -> dict:
        """
        Returns credential metadata (never the secret value), or None when it does not exist.
        """
        self.__validate_credentials_id(credentials_id)
        response = self.__request('GET', f'{self.__credential_path(credentials_id)}/api/json',
                                  expected_statuses=(200, 404))
        if response.status_code == 404:
            return None
        return self.__parse_json_object(response)

    def list_credentials(self) -> list:
        """
        Lists credential metadata of the global system domain. Metadata never contains secrets.
        """
        # Stapler exports the credential wrappers' fields at depth 1; at the default depth 0 each
        # element of the list contains only '_class'.
        response = self.__request('GET', f'{CREDENTIALS_STORE_PATH}/api/json?depth=1')
        data = self.__parse_json_object(response)
        credentials = data.get('credentials', [])
        if not isinstance(credentials, list):
            raise JenkinsOperationsError('Jenkins returned an invalid JSON response')
        return credentials

    def create_secret(self, credentials_id: str, secret: str, description: str = ''):
        """
        Creates a secret-text credential in the global system domain.
        :param credentials_id: New credential id.
        :param secret: Secret value.
        :param description: Optional description.
        """
        self.__validate_credentials_id(credentials_id)
        self.__validate_secret(secret)
        payload = {
            '': '0',
            'credentials': {
                'scope': 'GLOBAL',
                'id': credentials_id,
                'description': description,
                'secret': secret,
                '$class': STRING_CREDENTIAL_CLASS,
            },
        }
        self.__post(f'{CREDENTIALS_STORE_PATH}/createCredentials',
                    expected_statuses=(200, 201, 204),
                    data={'json': json.dumps(payload)})
        logger.info('Created the Jenkins credential')

    def update_secret(self, credentials_id: str, secret: str, description: str = None):
        """
        Updates the secret value (the key) of an existing secret-text credential by rewriting its
        config.xml. Requires the credentials plugin to allow the update.
        :param credentials_id: Existing credential id.
        :param secret: New secret value.
        :param description: When given, replaces the description; None preserves it.
        """
        self.__validate_credentials_id(credentials_id)
        self.__validate_secret(secret)
        path = f'{self.__credential_path(credentials_id)}/config.xml'
        response = self.__request('GET', path, expected_statuses=(200, 404))
        if response.status_code == 404:
            raise JenkinsOperationsError('Jenkins credential was not found', status_code=404)
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            raise JenkinsOperationsError('Jenkins credential config.xml could not be parsed') from None
        # Writing a <secret> element into a username/password or SSH credential would corrupt it.
        if not root.tag.endswith(STRING_CREDENTIAL_CLASS_SUFFIX):
            raise JenkinsOperationsError(
                'Jenkins credential is not a secret text credential; update_secret only updates '
                'secret text credentials')
        secret_element = root.find('secret')
        if secret_element is None:
            secret_element = ET.SubElement(root, 'secret')
        secret_element.text = secret
        if description is not None:
            description_element = root.find('description')
            if description_element is None:
                description_element = ET.SubElement(root, 'description')
            description_element.text = description
        body = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        self.__post(path, expected_statuses=(200, 201, 204), data=body,
                    headers={'Content-Type': 'application/xml'})
        logger.info('Updated the Jenkins credential')

    def delete_secret(self, credentials_id: str) -> bool:
        """
        Deletes a credential.
        :return: True when deleted, False when it did not exist (idempotent delete).
        """
        self.__validate_credentials_id(credentials_id)
        response = self.__post(f'{self.__credential_path(credentials_id)}/doDelete',
                               expected_statuses=(200, 201, 204, 404))
        if response.status_code == 404:
            logger.info('Jenkins credential was not found; nothing to delete')
            return False
        logger.info('Deleted the Jenkins credential')
        return True

    def write_secret(self, credentials_id: str, secret: str, description: str = '') -> str:
        """
        Creates the credential when it does not exist, otherwise updates its secret value.
        :param credentials_id: Credential id.
        :param secret: Secret value.
        :param description: Description used on create and on update (empty preserves an
            existing description).
        :return: 'created' or 'updated'.
        """
        self.__validate_credentials_id(credentials_id)
        self.__validate_secret(secret)
        if self.credential_exists(credentials_id):
            self.update_secret(credentials_id, secret, description=description or None)
            return 'updated'
        self.create_secret(credentials_id, secret, description=description)
        return 'created'
