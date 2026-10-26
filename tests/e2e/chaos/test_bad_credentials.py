"""Chaos test: invalid database credentials.

Starts an API rollout whose pods read an invalid database password. 
Verifies that the new pods fail at startup while the existing pods keep serving traffic.
"""
from support.waiting import wait_until


def test_new_pods_crashloop_while_old_pods_keep_serving(settings, cluster, api, broken_db_credentials):
    since = broken_db_credentials

    wait_until(lambda: cluster.crashing_pods_since(settings.api_deployment, since),
               timeout=150, interval=5, desc="new API pod crash-looping on invalid password")

    assert api.is_healthy(), "existing API pods must keep serving during a failed rollout"