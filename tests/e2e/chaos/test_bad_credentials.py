"""Chaos test: invalid database credentials.

Replaces the database password with an invalid value and restarts the API.
Verifies that the new pods fail at startup while the rolling update keeps the existing pods serving traffic.
"""
from datetime import datetime, timedelta, timezone

from support.waiting import wait_until


def test_new_pods_crashloop_on_wrong_password(settings, cluster, api, broken_db_credentials):
    since = datetime.now(timezone.utc) - timedelta(seconds=2)

    cluster.restart(settings.api_deployment)

    # The rolling update keeps the previous ReplicaSet serving until new pods are Ready.
    wait_until(lambda: cluster.crashing_pods_since(settings.api_deployment, since),
               timeout=150, interval=5, desc="new API pod crash-looping")