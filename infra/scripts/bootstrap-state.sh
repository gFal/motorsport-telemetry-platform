#!/usr/bin/env bash
# Creates the Terraform state backend.
set -euo pipefail
: "${RG:?}" "${LOCATION:?}" "${SA_NAME:?}"      # source ~/.motorsport-ci.env first

az provider register --namespace Microsoft.Storage --wait

az group show -n "$RG" >/dev/null 2>&1 || az group create -n "$RG" -l "$LOCATION" -o none

az storage account show -n "$SA_NAME" -g "$RG" >/dev/null 2>&1 || az storage account create \
  -n "$SA_NAME" -g "$RG" -l "$LOCATION" --sku Standard_LRS --kind StorageV2 \
  --min-tls-version TLS1_2 --https-only true --allow-blob-public-access false -o none

az storage account blob-service-properties update --account-name "$SA_NAME" -g "$RG" \
  --enable-versioning true --enable-delete-retention true --delete-retention-days 14 \
  --enable-container-delete-retention true --container-delete-retention-days 14 -o none

az storage container create --name tfstate --account-name "$SA_NAME" --auth-mode login -o none

az lock show --name protect-tfstate -g "$RG" --resource-name "$SA_NAME" \
  --resource-type Microsoft.Storage/storageAccounts >/dev/null 2>&1 || \
  az lock create --name protect-tfstate --lock-type CanNotDelete -g "$RG" \
  --resource-name "$SA_NAME" --resource-type Microsoft.Storage/storageAccounts -o none

echo "State backend ready: $SA_NAME/tfstate"