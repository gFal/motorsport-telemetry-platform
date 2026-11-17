# Operations

Runbooks for setting up and operating the live environment. Commands are run on the on-premises Ubuntu server from the repository checkout at `~/motorsport`, unless stated otherwise.

- [One-time setup](#one-time-setup)
- [Bring the Azure agent node up or down](#bring-the-azure-agent-node-up-or-down)
- [Change infrastructure with Terraform](#change-infrastructure-with-terraform)
- [Deployments and rollback](#deployments-and-rollback)
- [Chaos tests](#chaos-tests)
- [Rotate the External Secrets credential](#rotate-the-external-secrets-credential)

## One-time setup

The setup is done in this order. Each Terraform stack keeps its own state file in the same storage container.

1. **Resource group.** Create the `motorsport` resource group by hand. Terraform only reads it, so `terraform destroy` can never remove it.

2. **State backend.** Create the versioned, delete-locked storage account for Terraform state:

   ```bash
   source ~/.motorsport-ci.env        # exports RG, LOCATION, SA_NAME
   infra/scripts/bootstrap-state.sh
   ```

3. **CI identities** (`infra/terraform/bootstrap`). Applied by a human with `az login`. It creates two Entra ID applications with GitHub OIDC federation: a read-only *plan* identity for pull requests and a *Contributor* identity for the `production` environment.

   ```bash
   terraform -chdir=infra/terraform/bootstrap init
   terraform -chdir=infra/terraform/bootstrap apply -var "state_storage_account=$SA_NAME"
   ```

   Store the outputs as repository secrets: `AZURE_CLIENT_ID_PLAN`, `AZURE_CLIENT_ID_APPLY`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

4. **Key Vault** (`infra/terraform/platform`). Creates the vault and the service principal External Secrets Operator uses to read it.

   ```bash
   terraform -chdir=infra/terraform/platform init
   terraform -chdir=infra/terraform/platform apply -var "key_vault_name=<globally-unique-name>"
   ```

   Then add the database password to the vault as `postgres-password`, and give the cluster the read credential:

   ```bash
   kubectl create secret generic azure-kv-credentials \
     --from-literal=client-id="$(terraform -chdir=infra/terraform/platform output -raw eso_client_id)" \
     --from-literal=client-secret="$(terraform -chdir=infra/terraform/platform output -raw eso_client_secret)" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

   Update `vaultUrl` and `tenantId` in `k3s/overlays/prod/secretstore.yaml` if the vault changes.

5. **External Secrets Operator.** Installed with Helm, outside the application pipeline:

   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm upgrade --install external-secrets external-secrets/external-secrets \
     --namespace external-secrets --create-namespace \
     -f k3s/cluster-addons/external-secrets/values.yaml
   ```

6. **Agent variables.** Copy `infra/terraform/agent/terraform.tfvars.example` to `terraform.tfvars` and fill it in. Store the same content as the `TFVARS` repository secret (`agent-lifecycle.sh` keeps it in sync afterwards).

7. **GitHub.**
   - Create the `production` environment with a required reviewer. It gates `terraform apply`.
   - Register a self-hosted runner on the server with the label `motorsport-server`, under a dedicated user with `kubectl` access to the cluster.

## Bring the Azure agent node up or down

The agent VM costs money while it runs, so it is created only when needed. The script refreshes the home IP in the SSH firewall rule, applies Terraform, hardens the VM with Ansible, joins it to the tailnet and then to k3s.

```bash
export TAILSCALE_AUTHKEY_AGENT=tskey-auth-...   # ephemeral key
infra/scripts/agent-lifecycle.sh up
```

```bash
infra/scripts/agent-lifecycle.sh down
```

`down` removes the k3s node object first, then destroys only the VM and its networking. The resource group, Key Vault and Terraform state are untouched.

The Ansible inventory (`infra/ansible/inventory.ini`, group `azure_agent`) is kept on the server and is not committed.

## Change infrastructure with Terraform

1. Open a pull request. The `plan-and-lint` job posts the `infra/terraform/agent` plan to the job summary, using the read-only identity.
2. After merging, run **Actions → motorsport-pipeline → Run workflow** on `main` and approve the `production` environment.

The apply job stops if the agent VM is not running (CI never creates it) or if the plan would delete or replace any resource, because a replaced VM would not be re-joined to the cluster. Use `agent-lifecycle.sh` for those cases.

The `bootstrap` and `platform` stacks are applied by hand only.

## Deployments and rollback

Every push to `main` is deployed by the self-hosted runner: images are verified against their provenance attestation, deployed with `scripts/deploy.sh apply <sha>` and smoke-tested. A passing commit is recorded in the `deploy-state` ConfigMap as the last known-good version.

If deployment or the smoke tests fail, the pipeline redeploys the last known-good commit (the database is excluded) and re-runs its smoke tests. The cluster is then behind `main`, so open a revert pull request for the failed commit.

Manual operations:

```bash
export IMAGE_REGISTRY=ghcr.io/gfal

scripts/deploy.sh last-good                  # last commit that passed verification
scripts/deploy.sh diff <sha>                 # preview the changes a deployment would make
scripts/deploy.sh rollback <sha> <checkout>  # redeploy applications from another commit's checkout
```

## Chaos tests

Run the suite against the live cluster from **Actions → resilience → Run workflow**. It shares a concurrency group with deployments, so it waits for any deployment in progress. Scheduled runs that waited more than two hours for the runner (server switched off) are skipped.

| Test | Automated | Notes |
|---|---|---|
| Database outage | Yes | Scales PostgreSQL to zero; API must answer 5xx, then recover |
| Pod failure | Yes | Deletes every API pod; replacements must become healthy |
| Bad credentials | Yes | A rollout with a wrong password must never replace working pods |
| Disk pressure | No (`manual`) | Fills the server's root filesystem |
| Silent car | Skipped (`needs_simulator`) | Needs a remote stop/start hook in the simulator |

To run the manual test from the server, set the same environment variables as `resilience.yml` and run:

```bash
python -m pytest tests/e2e/chaos -m manual -v
```

## Rotate the External Secrets credential

The External Secrets client secret is valid for 365 days and is replaced on the first `platform` apply after 300 days. Check the expiry, re-apply, and update the cluster secret:

```bash
terraform -chdir=infra/terraform/platform output eso_client_secret_expires
terraform -chdir=infra/terraform/platform apply -var "key_vault_name=<name>"
# then re-create azure-kv-credentials as in step 4 of the one-time setup
```
