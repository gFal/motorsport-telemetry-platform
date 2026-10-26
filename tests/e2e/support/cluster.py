"""Kubernetes API access for the end-to-end test suites.

Wraps the official Kubernetes Python client with the operations the suites need: inspecting and scaling Deployments, managing pods, executing commands
in containers and reading Secrets and Services. Credentials are loaded from the local kubeconfig, falling back to in-cluster configuration.
"""
from datetime import datetime, timezone

from kubernetes import client, config
from kubernetes.stream import stream

from support.waiting import wait_until


class Cluster:
    def __init__(self, namespace: str):
        try:
            config.load_kube_config()       
        except config.ConfigException:
            config.load_incluster_config()  
        self.ns = namespace
        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()

    # nodes 
    def ready_nodes(self) -> list[str]:
        return [
            n.metadata.name
            for n in self.core.list_node().items
            if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions or [])
        ]

    # deployments 
    def selector(self, deployment: str) -> str:
        labels = self.apps.read_namespaced_deployment(deployment, self.ns).spec.selector.match_labels
        return ",".join(f"{k}={v}" for k, v in labels.items())

    def scale(self, deployment: str, replicas: int) -> None:
        self.apps.patch_namespaced_deployment_scale(deployment, self.ns, {"spec": {"replicas": replicas}})

    def restart(self, deployment: str) -> None:
        """Equivalent of `kubectl rollout restart`."""
        stamp = datetime.now(timezone.utc).isoformat()
        body = {"spec": {"template": {"metadata": {"annotations": {
            "kubectl.kubernetes.io/restartedAt": stamp}}}}}
        self.apps.patch_namespaced_deployment(deployment, self.ns, body)

    def is_rolled_out(self, deployment: str) -> bool:
        """Equivalent of a finished `kubectl rollout status`."""
        d = self.apps.read_namespaced_deployment(deployment, self.ns)
        want, s = d.spec.replicas or 0, d.status
        return ((s.observed_generation or 0) >= (d.metadata.generation or 0)
                and (s.updated_replicas or 0) == want
                and (s.available_replicas or 0) == want
                and (s.replicas or 0) == want)

    def wait_rolled_out(self, deployment: str, timeout: float = 180) -> None:
        wait_until(lambda: self.is_rolled_out(deployment), timeout=timeout, interval=3,
                   desc=f"rollout of {deployment}")

    # pods 
    def pods(self, deployment: str) -> list:
        """Pods of a Deployment, excluding ones already terminating."""
        items = self.core.list_namespaced_pod(self.ns, label_selector=self.selector(deployment)).items
        return [p for p in items if p.metadata.deletion_timestamp is None]

    @staticmethod
    def is_ready(pod) -> bool:
        statuses = pod.status.container_statuses or []
        return bool(statuses) and all(c.ready for c in statuses)

    def all_ready(self, deployment: str) -> bool:
        pods = self.pods(deployment)
        return bool(pods) and all(self.is_ready(p) for p in pods)

    def delete_pods(self, deployment: str) -> None:
        self.core.delete_collection_namespaced_pod(self.ns, label_selector=self.selector(deployment))

    def crashing_pods_since(self, deployment: str, since: datetime) -> list[str]:
        """Pods created after `since` that are crash-looping or have restarted."""
        crashing = []
        for p in self.pods(deployment):
            if p.metadata.creation_timestamp < since:
                continue
            for c in p.status.container_statuses or []:
                waiting = c.state.waiting if c.state else None
                if (waiting and waiting.reason == "CrashLoopBackOff") or c.restart_count >= 1:
                    crashing.append(p.metadata.name)
                    break
        return crashing

    def exec_in(self, deployment: str, command: list[str], timeout: int = 60) -> str:
        """Run a command in a ready pod of the Deployment and return its stdout."""
        pod = next((p for p in self.pods(deployment) if self.is_ready(p)), None)
        if pod is None:
            raise RuntimeError(f"no ready pod for deployment {deployment}")
        resp = stream(self.core.connect_get_namespaced_pod_exec, pod.metadata.name, self.ns,
                      command=command, stdin=False, stdout=True, stderr=True, tty=False,
                      _preload_content=False)
        resp.run_forever(timeout=timeout)
        out, err, rc = resp.read_stdout(), resp.read_stderr(), resp.returncode
        resp.close()
        if rc != 0:
            raise RuntimeError(f"{command!r} exited with {rc}: {err.strip()}")
        return out

    # secrets / services 
    def secret_value(self, name: str, key: str) -> str:
        """Base64-encoded value, exactly as stored in the Secret."""
        return self.core.read_namespaced_secret(name, self.ns).data[key]

    def set_secret_value(self, name: str, key: str, b64_value: str) -> None:
        self.core.patch_namespaced_secret(name, self.ns, {"data": {key: b64_value}})

    def service_url(self, name: str) -> str:
        """http://<ClusterIP>:<port> — routable from any cluster node, including the runner's."""
        svc = self.core.read_namespaced_service(name, self.ns)
        return f"http://{svc.spec.cluster_ip}:{svc.spec.ports[0].port}"

    def create_or_replace_secret(self, name: str, data_b64: dict) -> None:
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, labels={"purpose": "chaos-test"}),
            type="Opaque", data=data_b64)
        try:
            self.core.create_namespaced_secret(self.ns, body)
        except client.ApiException as exc:
            if exc.status != 409:
                raise
            self.core.replace_namespaced_secret(name, self.ns, body)

    def delete_secret(self, name: str) -> None:
        try:
            self.core.delete_namespaced_secret(name, self.ns)
        except client.ApiException as exc:
            if exc.status != 404:
                raise

    def swap_secret_ref(self, deployment: str, old: str, new: str) -> None:
        """Replace every envFrom reference to Secret ``old`` with ``new``.

        Changing the pod template starts a rollout of the Deployment.
        """
        d = self.apps.read_namespaced_deployment(deployment, self.ns)
        to_dict = self.apps.api_client.sanitize_for_serialization
        containers = []
        for c in d.spec.template.spec.containers:
            env_from = []
            for src in c.env_from or []:
                entry = to_dict(src)
                if src.secret_ref and src.secret_ref.name == old:
                    entry["secretRef"]["name"] = new
                env_from.append(entry)
            containers.append({"name": c.name, "envFrom": env_from})
        # Strategic merge patch: containers merge by name - envFrom has no merge key and is replaced whole.
        self.apps.patch_namespaced_deployment(
            deployment, self.ns, {"spec": {"template": {"spec": {"containers": containers}}}})