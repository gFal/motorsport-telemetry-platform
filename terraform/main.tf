terraform {
  required_version = "~> 1.16.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
}

provider "azurerm" {
  features {}

  resource_provider_registrations = "none"
}

# Created once, by hand, and never managed by Terraform. Also holds the tf state storage account, 
# so terraform destroy must never be able to destroy it through agent-lifecycle.sh down.
data "azurerm_resource_group" "motorsport" {
  name = var.resource_group_name
}

resource "azurerm_virtual_network" "motorsport" {
  name                = "motorsport-vnet"
  address_space       = ["10.10.0.0/16"]
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name
}

resource "azurerm_subnet" "agent" {
  name                 = "agent-subnet"
  resource_group_name  = data.azurerm_resource_group.motorsport.name
  virtual_network_name = azurerm_virtual_network.motorsport.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_public_ip" "agent" {
  name                = "motorsport-agent-pip"
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "agent" {
  name                = "motorsport-agent-nsg"
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name

  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.ssh_allowed_cidr
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowTailscale"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Udp"
    source_port_range          = "*"
    destination_port_range     = "41641"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

}

resource "azurerm_subnet_network_security_group_association" "agent" {
  subnet_id                 = azurerm_subnet.agent.id
  network_security_group_id = azurerm_network_security_group.agent.id
}

resource "azurerm_network_interface" "agent" {
  name                = "motorsport-agent-nic"
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.agent.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.agent.id
  }
}

resource "azurerm_linux_virtual_machine" "agent" {
  name                = var.vm_name
  location            = data.azurerm_resource_group.motorsport.location
  resource_group_name = data.azurerm_resource_group.motorsport.name
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids           = [azurerm_network_interface.agent.id]
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.admin_ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }
}