"""PostgreSQL access for the end-to-end test suites.

Queries are executed with psql inside the database pod through the Kubernetes exec API, so the test runner needs neither a network route to the database nor its credentials.
"""
from support.cluster import Cluster
from support.config import Settings


class Database:
    def __init__(self, cluster: Cluster, settings: Settings):
        self.cluster = cluster
        self.settings = settings

    def scalar(self, query: str) -> str:
        """Run one SQL statement and return the single value it produces, as text."""
        out = self.cluster.exec_in(self.settings.postgres_deployment, [
            "psql", "-U", self.settings.db_user, "-d", self.settings.db_name,
            "-v", "ON_ERROR_STOP=1", "-tAc", query,
        ])
        return out.strip()

    def now(self) -> str:
        """The database's clock: compare timestamps against this, not the runner's."""
        return self.scalar("SELECT now()")