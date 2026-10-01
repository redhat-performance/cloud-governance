import os

import pytest
from elastic_transport import Transport as ElasticTransport
from opensearchpy.transport import Transport as OpenSearchTransport

from cloud_governance.main.environment_variables import environment_variables

# EnvironmentVariables.get_env resolves a key case-insensitively, so every
# spelling that could reach it has to be cleared.
ES_ENV_VARS = ('es_host', 'ES_HOST', 'es_port', 'ES_PORT',
               'es_user', 'ES_USER', 'es_password', 'ES_PASSWORD')

# Keys that gate the live client in ElasticUpload / ElasticSearchOperations.
ES_CONFIG_KEYS = ('es_host', 'es_port', 'es_user', 'es_password')


@pytest.fixture(autouse=True, scope='session')
def clear_es_environment():
    """
    This method removes the ElasticSearch/OpenSearch connection settings from the
    process environment for the whole unit test session, so a developer or CI
    machine that exports them cannot make the unit tests talk to a real cluster.
    @return:
    """
    original_values = {var: os.environ.pop(var) for var in ES_ENV_VARS if var in os.environ}
    yield
    os.environ.update(original_values)


@pytest.fixture(autouse=True)
def block_elasticsearch_uploads():
    """
    This method blanks the ElasticSearch/OpenSearch settings in the environment
    variables singleton before every unit test. The singleton is built once at
    import time and mutated in place by the tests, so clearing os.environ alone
    is not enough. With no es_host, ElasticUpload keeps its client as None and
    the policies run without uploading.
    @return:
    """
    for key in ES_CONFIG_KEYS:
        environment_variables.environment_variables_dict[key] = ''
    yield


@pytest.fixture(autouse=True)
def fail_on_elasticsearch_call(monkeypatch):
    """
    This method makes a live ElasticSearch/OpenSearch request fail loudly in the
    unit tests. Both clients funnel every request through Transport.perform_request,
    so blocking it there covers the whole API. The mock_elasticsearch decorator
    patches OpenSearch.index and OpenSearch.search, which sit above the transport,
    so the tests that exercise ElasticSearchOperations on purpose are unaffected.
    @return:
    """
    def refuse_request(self, method: str, url: str, *args, **kwargs):
        raise RuntimeError(
            f'Unit test tried to reach a live ElasticSearch/OpenSearch server: {method} {url}. '
            f'Use tests.unittest.mocks.elasticsearch.mock_elasticsearch instead.'
        )

    monkeypatch.setattr(OpenSearchTransport, 'perform_request', refuse_request)
    monkeypatch.setattr(ElasticTransport, 'perform_request', refuse_request)
    yield
