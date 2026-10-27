variable "resource_group_name" {
  description = "Existing resource group."
  type        = string
  default     = "motorsport"
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

variable "admin_ssh_public_key" {
  description = "Contents of ~/.ssh/azure_motorsport.pub (a public key, not a path)."
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "Public IP of the Ubuntu server (x.x.x.x/32): the only source allowed to reach the agent, for SSH and Tailscale's direct WireGuard path."
  type        = string
  sensitive   = true
}