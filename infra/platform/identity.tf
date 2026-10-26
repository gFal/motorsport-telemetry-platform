# Entra ID identity used by External Secrets Operator to read Key Vault.

resource "azuread_application" "eso" {
  display_name = "motorsport-eso"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "eso" {
  client_id = azuread_application.eso.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# Client secret rotation: the secret is replaced on the first apply after 300 days.
# Each secret is valid for 365 days, leaving a 65-day window for that apply.
resource "time_rotating" "eso_secret" {
  rotation_days = 300
}

resource "azuread_application_password" "eso" {
  application_id = azuread_application.eso.id
  display_name   = "eso-k3s-${formatdate("YYYYMM", time_rotating.eso_secret.id)}"
  end_date       = timeadd(time_rotating.eso_secret.id, "8760h")

  rotate_when_changed = {
    rotation = time_rotating.eso_secret.id
  }
}