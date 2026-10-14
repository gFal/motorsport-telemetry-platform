"""Session-wide fixtures"""
import pytest

from support.api import ApiClient
from support.cluster import Cluster
from support.config import Settings
from support.db import Database


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def cluster(settings) -> Cluster:
    return Cluster(settings.namespace)


@pytest.fixture(scope="session")
def api(settings, cluster) -> ApiClient:
    return ApiClient(settings.api_url or cluster.service_url(settings.api_service))


@pytest.fixture(scope="session")
def db(cluster, settings) -> Database:
    return Database(cluster, settings)