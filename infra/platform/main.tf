terraform {
  required_version = "~> 1.16.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }

  # Shared state container - this stack has its own state key and is never affected by operations on the agent stack.
  backend "azurerm" {
    resource_group_name  = "motorsport"
    storage_account_name = "motorsporttfed44045c"
    container_name       = "tfstate"
    key                  = "motorsport-platform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  resource_provider_registrations = "none"

  features {
    key_vault {
      # Purge protection prevents purging - destroy leaves the vault soft-deleted.
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" {}

data "azuread_client_config" "current" {}

# Managed outside Terraform.
data "azurerm_resource_group" "motorsport" {
  name = var.resource_group_name
}

locals {
  secrets_officer_object_id = coalesce(var.secrets_officer_object_id, data.azuread_client_config.current.object_id)
}

# Entra ID identity used by External Secrets Operator to read Key Vault.

resource "azuread_application" "eso" {
  display_name = "motorsport-eso"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "eso" {
  client_id = azuread_application.eso.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# Client secret rotation: the secret is replaced on the first apply after 300 days.
# Each secret is valid for 365 days, leaving a 65-day window for that apply.
resource "time_rotating" "eso_secret" {
  rotation_days = 300
}

resource "azuread_application_password" "eso" {
  application_id = azuread_application.eso.id
  display_name   = "eso-k3s-${formatdate("YYYYMM", time_rotating.eso_secret.id)}"
  end_date       = timeadd(time_rotating.eso_secret.id, "8760h")

  rotate_when_changed = {
    rotation = time_rotating.eso_secret.id
  }
}

# Key Vault and access

resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name
  tenant_id           = data.azuread_client_config.current.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  purge_protection_enabled   = true # cannot be disabled once enabled
  soft_delete_retention_days = 7

  # Access is controlled by Entra ID authentication and RBAC - network ACLs are not applied.
  public_network_access_enabled = true
}

resource "azurerm_role_assignment" "secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = local.secrets_officer_object_id
}

resource "azurerm_role_assignment" "eso_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azuread_service_principal.eso.object_id
  principal_type       = "ServicePrincipal"
}