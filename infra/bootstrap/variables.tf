variable "oidc_repo" {
  description = "GitHub repo in the OIDC subject format (immutable: owner@id/repo@id)."
  type        = string
  default     = "gFal@92217105/motorsport-telemetry-platform@1353949219"
}

variable "resource_group_name" {
  type    = string
  default = "motorsport"
}

variable "state_storage_account" {
  description = "Terraform state storage account (echo $SA_NAME)."
  type        = string
}