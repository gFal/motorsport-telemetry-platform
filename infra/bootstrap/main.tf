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
  }

  backend "azurerm" {
    resource_group_name  = "motorsport"
    storage_account_name = "motorsporttfed44045c"
    container_name       = "tfstate"
    key                  = "motorsport-bootstrap.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

provider "azuread" {} # uses az login, like azurerm

data "azuread_client_config" "current" {}

# Manually created, read only (never managed here either).
data "azurerm_resource_group" "motorsport" {
  name = var.resource_group_name
}

data "azurerm_storage_account" "tfstate" {
  name                = var.state_storage_account
  resource_group_name = data.azurerm_resource_group.motorsport.name
}

locals {
  github_issuer = "https://token.actions.githubusercontent.com"
  tfstate_scope = "${data.azurerm_storage_account.tfstate.id}/blobServices/default/containers/tfstate"

  identities = {
    plan = {
      display_name = "motorsport-ci-plan"
      fic_name     = "plan-pull-request"
      subject      = "repo:${var.oidc_repo}:pull_request"
      rg_role      = "Reader"
      state_role   = "Storage Blob Data Reader"
    }
    apply = {
      display_name = "motorsport-ci-apply"
      fic_name     = "apply-production-env"
      subject      = "repo:${var.oidc_repo}:environment:production"
      rg_role      = "Contributor"
      state_role   = "Storage Blob Data Contributor"
    }
  }
}

resource "azuread_application" "ci" {
  for_each     = local.identities
  display_name = each.value.display_name
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "ci" {
  for_each  = local.identities
  client_id = azuread_application.ci[each.key].client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_federated_identity_credential" "ci" {
  for_each       = local.identities
  application_id = azuread_application.ci[each.key].id
  display_name   = each.value.fic_name
  issuer         = local.github_issuer
  subject        = each.value.subject
  audiences      = ["api://AzureADTokenExchange"]
}

resource "azurerm_role_assignment" "rg" {
  for_each             = local.identities
  scope                = data.azurerm_resource_group.motorsport.id
  role_definition_name = each.value.rg_role
  principal_id         = azuread_service_principal.ci[each.key].object_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "state" {
  for_each             = local.identities
  scope                = local.tfstate_scope
  role_definition_name = each.value.state_role
  principal_id         = azuread_service_principal.ci[each.key].object_id
  principal_type       = "ServicePrincipal"
}