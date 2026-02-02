terraform {
  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = ">= 2.9.14"
    }
  }
}

########################
# Provider Proxmox
########################

provider "proxmox" {
  pm_api_url      = var.pm_api_url
  pm_user         = var.pm_user
  pm_password     = var.pm_password
  pm_tls_insecure = true
}

########################
# LXC Container
########################

resource "proxmox_lxc" "supervision" {

  target_node = var.node_name
  vmid        = var.vmid

  hostname    = var.hostname
  ostemplate  = var.template

  cores       = var.cores
  memory      = var.memory
  swap        = 512

  start       = true
  onboot      = true

  rootfs {
    storage = var.storage
    size    = "4G"
  }

  network {
    name   = "eth0"
    bridge = "vmbr0"
    ip     = "dhcp"
  }

  features {
    nesting = true
  }
}
