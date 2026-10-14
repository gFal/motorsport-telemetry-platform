"""Chaos test: database outage.

Scales PostgreSQL to zero replicas and verifies that database-backed API endpoints fail with a 5xx status 
during the outage and recover without intervention once the database is restored.
"""
from support.waiting import wait_until


def test_api_returns_5xx_during_outage_and_recovers(settings, cluster, api):
    probe = settings.db_probe_path  # must query the database --> /health does not
    assert api.status(probe) < 500, f"{probe} must work before the outage"

    cluster.scale(settings.postgres_deployment, 0)
    wait_until(lambda: api.status(probe) >= 500, timeout=60, desc=f"{probe} returns 5xx")

    cluster.scale(settings.postgres_deployment, 1)
    cluster.wait_rolled_out(settings.postgres_deployment, timeout=180)
    wait_until(lambda: api.status(probe) < 500, timeout=120, desc=f"{probe} recovers")