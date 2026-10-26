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