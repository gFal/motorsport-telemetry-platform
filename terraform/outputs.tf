output "agent_public_ip" {
  description = "Public IP of the Azure VM."
  value       = azurerm_public_ip.agent.ip_address
}

output "ssh_command" {
  description = "Ready-to-use SSH command."
  value       = "ssh -i ~/.ssh/azure_motorsport ${var.admin_username}@${azurerm_public_ip.agent.ip_address}"
}