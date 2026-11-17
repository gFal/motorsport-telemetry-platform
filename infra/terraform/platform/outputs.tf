output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "tenant_id" {
  value = data.azuread_client_config.current.tenant_id
}

output "eso_client_id" {
  value = azuread_application.eso.client_id
}

output "eso_client_secret" {
  value     = azuread_application_password.eso.value
  sensitive = true
}

output "eso_client_secret_expires" {
  value = azuread_application_password.eso.end_date
}