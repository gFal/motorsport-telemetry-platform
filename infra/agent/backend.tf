terraform {
  backend "azurerm" {
    resource_group_name  = "motorsport"
    storage_account_name = "motorsporttfed44045c"
    container_name       = "tfstate"
    key                  = "motorsport-agent.tfstate"
    use_azuread_auth     = true
  }
}