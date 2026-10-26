variable "resource_group_name" {
  description = "Existing resource group for long-lived platform resources."
  type        = string
  default     = "motorsport"
}

variable "key_vault_name" {
  description = "Globally unique Key Vault name (3-24 characters)."
  type        = string
}

variable "secrets_officer_object_id" {
  description = "Entra ID object ID granted Key Vault Secrets Officer. Defaults to the identity running Terraform."
  type        = string
  default     = null
}