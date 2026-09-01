variable "resource_group_name" {
  description = "VM resource group."
  type        = string
  default     = "motorsport"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "swedencentral"
}

variable "vm_name" {
  description = "Azure VM name"
  type        = string
  default     = "motorsport-agent"
}

variable "vm_size" {
  description = "VM size"
  type        = string
  default     = "Standard_B2ats_v2"
}

variable "admin_username" {
  description = "Linux admin user created on the VM."
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "Path to local SSH public key."
  type        = string
  default     = "~/.ssh/azure_motorsport.pub"
}

variable "my_ip_cidr" {
  description = "Current public IP in CIDR form."
  type        = string
}