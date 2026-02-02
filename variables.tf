########################
# Proxmox
########################

variable "pm_api_url" {}
variable "pm_user" {}
variable "pm_password" {
  sensitive = true
}

########################
# Container config
########################

variable "node_name" {
  default = "pve"
}

variable "vmid" {
  default = 200
}

variable "hostname" {
  default = "supervision-proxmox"
}

variable "template" {
  default = "local:vztmpl/alpine-minirootfs-3.23.0-x86_64.tar.gz"
}

variable "cores" {
  default = 1
}

variable "memory" {
  default = 512
}

variable "storage" {
  default = "local-lvm"
}
