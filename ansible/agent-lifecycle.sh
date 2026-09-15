set -euo pipefail

TF_DIR="$HOME/motorsport/terraform"
ANSIBLE_DIR="$HOME/motorsport/ansible"
TF_OUTPUT_IP="agent_public_ip"          
AZURE_SSH_USER="azureuser"
AZURE_SSH_KEY="$HOME/.ssh/azure_motorsport"
AGENT_NODE_NAME="motorsport-agent"

up() {
  echo "==> terraform apply"
  (cd "$TF_DIR" && terraform apply -parallelism=1 -auto-approve)
  AZURE_IP=$(cd "$TF_DIR" && terraform output -raw "$TF_OUTPUT_IP")
  echo "    Azure VM public IP: $AZURE_IP"
  ssh-keygen -R "$AZURE_IP" >/dev/null 2>&1 || true

  echo "==> waiting for SSH on $AZURE_IP"
  until ssh -i "$AZURE_SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
      "$AZURE_SSH_USER@$AZURE_IP" true 2>/dev/null; do
    sleep 5
  done

  echo "==> hardening + joining the tailnet"
  ansible-playbook -i "$ANSIBLE_DIR/inventory.ini" "$ANSIBLE_DIR/playbook.yml" \
    --limit azure_agent \
    --extra-vars "tailscale_authkey=${TAILSCALE_AUTHKEY_AGENT:?set TAILSCALE_AUTHKEY_AGENT first}" \
    -e "ansible_host=$AZURE_IP"

  AZURE_TS_IP=$(ssh -i "$AZURE_SSH_KEY" "$AZURE_SSH_USER@$AZURE_IP" tailscale ip -4)
  UBUNTU_TS_IP=$(tailscale ip -4)
  echo "    Azure tailnet IP:  $AZURE_TS_IP"
  echo "    Ubuntu tailnet IP: $UBUNTU_TS_IP"

  echo "==> dropping any stale k3s node object from a previous cycle"
  sudo k3s kubectl delete node "$AGENT_NODE_NAME" --ignore-not-found

  echo "==> fetching the k3s join token"
  K3S_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token)

  echo "==> joining k3s as an agent"
  ssh -i "$AZURE_SSH_KEY" "$AZURE_SSH_USER@$AZURE_IP" \
    "curl -sfL https://get.k3s.io | K3S_URL=https://$UBUNTU_TS_IP:6443 K3S_TOKEN=$K3S_TOKEN \
     INSTALL_K3S_EXEC='--node-ip=$AZURE_TS_IP --flannel-iface=tailscale0 --node-name=$AGENT_NODE_NAME' sh -"

  echo "==> done — verifying"
  sudo k3s kubectl get nodes -o wide
}

down() {
  echo "==> dropping the k3s node object first (VM is about to disappear)"
  sudo k3s kubectl delete node "$AGENT_NODE_NAME" --ignore-not-found || true

  echo "==> terraform destroy"
  (cd "$TF_DIR" && terraform destroy -auto-approve)

  echo "==> done. The ephemeral Tailscale key means the tailnet entry drops on its own once it's offline."
}

case "${1:-}" in
  up)   up ;;
  down) down ;;
  *) echo "usage: $0 {up|down}"; exit 1 ;;
esac