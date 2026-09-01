terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  resource_provider_registrations = "none"
}

resource "azurerm_resource_group" "motorsport" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_virtual_network" "motorsport" {
  name                = "motorsport-vnet"
  address_space       = ["10.10.0.0/16"]
  location            = azurerm_resource_group.motorsport.location
  resource_group_name = azurerm_resource_group.motorsport.name
}

resource "azurerm_subnet" "agent" {
  name                 = "agent-subnet"
  resource_group_name  = azurerm_resource_group.motorsport.name
  virtual_network_name = azurerm_virtual_network.motorsport.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_public_ip" "agent" {
  name                = "motorsport-agent-pip"
  location            = azurerm_resource_group.motorsport.location
  resource_group_name = azurerm_resource_group.motorsport.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "agent" {
  name                = "motorsport-agent-nsg"
  location            = azurerm_resource_group.motorsport.location
  resource_group_name = azurerm_resource_group.motorsport.name

  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.my_ip_cidr
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
  location            = azurerm_resource_group.motorsport.location
  resource_group_name = azurerm_resource_group.motorsport.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.agent.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.agent.id
  }
}

resource "azurerm_linux_virtual_machine" "agent" {
  name                = var.vm_name
  resource_group_name = azurerm_resource_group.motorsport.name
  location            = azurerm_resource_group.motorsport.location
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids           = [azurerm_network_interface.agent.id]
  disable_password_authentication = true

  admin_ssh_key {
    username = var.admin_username
    # pathexpand() is required — file() does NOT expand "~" on its own.
    public_key = file(pathexpand(var.ssh_public_key_path))
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