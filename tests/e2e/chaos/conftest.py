"""Fixtures for the chaos test suite.

Each test deliberately disrupts the running platform. The fixtures in this module restore the baseline state afterwards, whether the test passes or fails.
"""
import base64
from datetime import datetime, timedelta, timezone

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
    """Point the API at a copy of the database Secret that holds an invalid password.

    The managed Secret is never modified: in production it is owned by External Secrets Operator and re-synchronised from Key Vault. 
    The Deployment's reference is restored and the copy deleted on teardown.

    Yields:
        The time immediately before the reference swap started the rollout.
    """
    broken = f"{settings.postgres_secret}-chaos"
    original = cluster.core.read_namespaced_secret(settings.postgres_secret, settings.namespace).data
    wrong = base64.b64encode(b"definitely-wrong").decode()
    cluster.create_or_replace_secret(broken, {**original, settings.postgres_secret_key: wrong})

    since = datetime.now(timezone.utc) - timedelta(seconds=2)
    cluster.swap_secret_ref(settings.api_deployment, settings.postgres_secret, broken)  # rollout starts
    try:
        yield since
    finally:
        cluster.swap_secret_ref(settings.api_deployment, broken, settings.postgres_secret)
        cluster.wait_rolled_out(settings.api_deployment, timeout=240)
        cluster.delete_secret(broken)