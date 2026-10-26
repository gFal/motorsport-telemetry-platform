data "azuread_client_config" "current" {}

# Managed outside Terraform.
data "azurerm_resource_group" "motorsport" {
  name = var.resource_group_name
}

locals {
  secrets_officer_object_id = coalesce(var.secrets_officer_object_id, data.azuread_client_config.current.object_id)
}

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