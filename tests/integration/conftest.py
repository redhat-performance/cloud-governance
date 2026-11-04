"""
Shared setup for the integration tests.
"""
import logging

import pytest

LOGGER_NAME = 'cloud_governance'


def pytest_configure(config):
    """Show the policy log lines while the tests run, without needing `pytest -s`."""
    config.option.log_cli = True
    config.option.log_cli_level = 'INFO'


@pytest.fixture(autouse=True, scope='session')
def enable_policy_logs():
    """
    Raise the policy logger to INFO for the integration session.

    cloud_governance.common.logger.init_logger never sets a level on its logger;
    main.py does that at runtime. Under pytest the effective level therefore falls
    back to WARNING and every INFO line emitted by a policy is dropped.
    """
    logger = logging.getLogger(LOGGER_NAME)
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    yield
    logger.setLevel(previous_level)
