#!/usr/bin/env bash
#
# Deploy the production overlay using the images built from a given commit.
#
# Usage:
#   deploy.sh diff      <sha> [root]  Show the changes a deployment would make.
#   deploy.sh apply     <sha> [root]  Apply all resources and wait for every rollout.
#   deploy.sh rollback  <sha> [root]  Apply all resources except tier=database; wait for application rollouts.
#   deploy.sh mark-good <sha>         Record <sha> as the last version that passed verification.
#   deploy.sh last-good               Print the last recorded known-good commit, if any.
#
# Arguments:
#   sha   Full 40-character commit SHA - also the image tag.
#   root  Repository checkout providing the manifests (default: the current checkout).
#
# Environment:
#   IMAGE_REGISTRY       Required. Registry path, e.g. ghcr.io/<owner>.
#   K8S_NAMESPACE        Default: default.
#   API_DEPLOYMENT       Default: motorsport-api.
#   ANOMALY_DEPLOYMENT   Default: motorsport-anomaly.
#   POSTGRES_DEPLOYMENT  Default: postgres.
set -euo pipefail

MODE=${1:?usage: deploy.sh <diff|apply|rollback|mark-good|last-good> [sha] [root]}
NS=${K8S_NAMESPACE:-default}
STATE_CM=deploy-state

if [ "$MODE" = "last-good" ]; then
  kubectl -n "$NS" get configmap "$STATE_CM" -o jsonpath='{.data.last_good_sha}' 2>/dev/null || true
  exit 0
fi

SHA=${2:?commit sha required}
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "deploy.sh: '$SHA' is not a full 40-character commit SHA" >&2; exit 2; }

if [ "$MODE" = "mark-good" ]; then
  kubectl -n "$NS" create configmap "$STATE_CM" \
    --from-literal=last_good_sha="$SHA" \
    --from-literal=last_good_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --dry-run=client -o yaml | kubectl apply -f -
  exit 0
fi

ROOT=$(cd "${3:-$(git rev-parse --show-toplevel)}" && pwd)
: "${IMAGE_REGISTRY:?set IMAGE_REGISTRY, e.g. ghcr.io/<owner>}"
API_DEPLOYMENT=${API_DEPLOYMENT:-motorsport-api}
ANOMALY_DEPLOYMENT=${ANOMALY_DEPLOYMENT:-motorsport-anomaly}
POSTGRES_DEPLOYMENT=${POSTGRES_DEPLOYMENT:-postgres}

# Temporary overlay that pins the image tags on top of the production overlay.
# It is created inside ROOT because Kustomize does not load resources from outside its directory tree.
WORK=$(mktemp -d "$ROOT/.deploy.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
cat > "$WORK/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../k3s/overlays/prod
images:
  - name: ${IMAGE_REGISTRY}/motorsport-api
    newTag: "${SHA}"
  - name: ${IMAGE_REGISTRY}/motorsport-anomaly
    newTag: "${SHA}"
EOF

case "$MODE" in
  diff)
    # kubectl diff exits 1 when differences exist and >1 on error.
    kubectl diff -k "$WORK" || [ $? -eq 1 ]
    ;;
  apply)
    kubectl apply -k "$WORK"
    for d in "$POSTGRES_DEPLOYMENT" "$API_DEPLOYMENT" "$ANOMALY_DEPLOYMENT"; do
      kubectl -n "$NS" rollout status "deploy/$d" --timeout=240s
    done
    ;;
  rollback)
    # Stateful components are excluded - database changes are rolled forward manually.
    kubectl kustomize "$WORK" | kubectl apply -l 'tier!=database' -f -
    for d in "$API_DEPLOYMENT" "$ANOMALY_DEPLOYMENT"; do
      kubectl -n "$NS" rollout status "deploy/$d" --timeout=240s
    done
    ;;
  *)
    echo "deploy.sh: unknown mode '$MODE'" >&2
    exit 2
    ;;
esac