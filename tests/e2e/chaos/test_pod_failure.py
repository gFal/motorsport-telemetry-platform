"""Chaos test: loss of API pods.

Deletes every pod of the API Deployment and verifies that Kubernetes schedules replacements and that the API returns to a healthy state.
"""
from support.waiting import wait_until


def test_deleted_api_pods_are_replaced_and_ready(settings, cluster, api):
    before = {p.metadata.name for p in cluster.pods(settings.api_deployment)}
    assert before, "no API pods found"

    cluster.delete_pods(settings.api_deployment)

    def replaced_and_ready():
        now = {p.metadata.name for p in cluster.pods(settings.api_deployment)}
        return cluster.all_ready(settings.api_deployment) and not (now & before)

    wait_until(replaced_and_ready, timeout=120, desc="replacement API pods Ready")
    wait_until(api.is_healthy, timeout=60, desc="/health 200")