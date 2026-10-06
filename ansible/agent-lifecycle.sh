#!/usr/bin/env bash
# agent-lifecycle.sh --> bring the Azure k3s agent up/down on demand.
# up: refresh home IP --> terraform apply --> Ansible hardening + Tailscale --> k3s join
# down: drop k3s node object --> terraform destroy (VM + networking only, the rg and the Terraform state storage are not managed by Terraform)
set -euo pipefail

TF_DIR="$HOME/motorsport/infra/agent"
ANSIBLE_DIR="$HOME/motorsport/ansible"
TF_OUTPUT_IP="agent_public_ip"          
AZURE_SSH_USER="azureuser"
AZURE_SSH_KEY="$HOME/.ssh/azure_motorsport"
AGENT_NODE_NAME="motorsport-agent"
GH_REPO="gFal/motorsport-telemetry-platform"  # keeping the CI TFVARS secret in sync
TF_LOCK_TIMEOUT="5m"                          # wait (don't fail) if a CI apply holds the state lock

# Replaces `data "http" "my_ip"` lookup in main.tf.
# Detects the current home public IP and writes it into terraform.tfvars.
# If it changed, it also re-uploads terraform.tfvars as the TFVARS secret, so CI
# plans/applies use the same value and never propose changing the SSH rule.
refresh_home_ip() {
  local tfvars="$TF_DIR/terraform.tfvars"
  local current

  current="$(curl -fsS --max-time 10 https://api.ipify.org)/32" \
    || { echo "!! could not detect the public IP (api.ipify.org)"; return 1; }

  if grep -q "^ssh_allowed_cidr *= *\"${current}\"" "$tfvars"; then
    echo "    home IP unchanged (${current})"
    return 0
  fi

  echo "    home IP is now ${current} — updating terraform.tfvars"
  if grep -q '^ssh_allowed_cidr' "$tfvars"; then
    sed -i "s|^ssh_allowed_cidr.*|ssh_allowed_cidr     = \"${current}\"|" "$tfvars"
  else
    echo "ssh_allowed_cidr     = \"${current}\"" >> "$tfvars"
  fi

  # A stale CI secret must not stop a local bring-up, but it must be visible.
  if gh secret set TFVARS --repo "$GH_REPO" < "$tfvars" >/dev/null 2>&1; then
    echo "    TFVARS secret updated in $GH_REPO"
  else
    echo "!! WARNING: could not update the TFVARS secret (gh not logged in?)."
    echo "!!          CI will use the old IP until you run:"
    echo "!!          gh secret set TFVARS --repo $GH_REPO < $tfvars"
  fi
}

up() {
  # Fail before creating anything billable: previously this was only checked after
  # terraform apply, which could leave a VM running but never joined.
  : "${TAILSCALE_AUTHKEY_AGENT:?set TAILSCALE_AUTHKEY_AGENT first}"

  echo "==> refreshing home IP for the NSG SSH rule"
  refresh_home_ip
  
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
  (cd "$TF_DIR" && terraform destroy -lock-timeout="$TF_LOCK_TIMEOUT" -auto-approve)

  echo "==> done. The ephemeral Tailscale key means the tailnet entry drops on its own once it's offline."
}

case "${1:-}" in
  up)   up ;;
  down) down ;;
  *) echo "usage: $0 {up|down}"; exit 1 ;;
esac