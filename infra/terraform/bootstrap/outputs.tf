output "plan_client_id" {
  value = azuread_application.ci["plan"].client_id
}

output "apply_client_id" {
  value = azuread_application.ci["apply"].client_id
}