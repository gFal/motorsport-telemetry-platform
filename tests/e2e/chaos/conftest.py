"""Fixtures for the chaos test suite.

Each test deliberately disrupts the running platform. The fixtures in this module restore the baseline state afterwards, whether the test passes or fails.
"""
import base64

import pytest

from support.waiting import wait_until


@pytest.fixture(autouse=True)
def restore_baseline(settings, cluster, api):
    """Return the platform to its steady state after every chaos test.

    Scales PostgreSQL back to one replica, waits for the PostgreSQL and API rollouts to complete and confirms that the API reports healthy.
    """
    yield
    cluster.scale(settings.postgres_deployment, 1)
    cluster.wait_rolled_out(settings.postgres_deployment, timeout=180)
    cluster.wait_rolled_out(settings.api_deployment, timeout=180)
    wait_until(api.is_healthy, timeout=120, desc="API healthy after chaos test")


@pytest.fixture
def broken_db_credentials(settings, cluster):
    """Replace the database password in the Secret with an invalid value.

    On teardown the original value is restored and the API Deployment is restarted, so its pods reconnect with valid credentials.
    """
    original = cluster.secret_value(settings.postgres_secret, settings.postgres_secret_key)
    wrong = base64.b64encode(b"definitely-wrong").decode()
    cluster.set_secret_value(settings.postgres_secret, settings.postgres_secret_key, wrong)
    yield
    cluster.set_secret_value(settings.postgres_secret, settings.postgres_secret_key, original)
    cluster.restart(settings.api_deployment)
    cluster.wait_rolled_out(settings.api_deployment, timeout=240)