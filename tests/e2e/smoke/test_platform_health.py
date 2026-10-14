""" Deployed platform up ? """
import pytest


def test_api_health_endpoint_returns_200(api):
    assert api.is_healthy()


@pytest.mark.parametrize("deployment_attr",
                         ["postgres_deployment", "api_deployment", "anomaly_deployment"])
def test_deployment_is_fully_available(settings, cluster, deployment_attr):
    name = getattr(settings, deployment_attr)
    assert cluster.is_rolled_out(name), f"deployment {name} is not fully available"


def test_server_node_is_ready(cluster):
    assert cluster.ready_nodes(), "no Ready nodes"