# ICTD Azure single-VM deployment — one multi-GPU HPC box, no cross-node fabric.
#
# This is a DELIBERATELY SIMPLER sibling of ../../terraform (AWS, 2 nodes + EFA + placement
# group). The current experiment is single-node NVML/GPU-telemetry only — it runs
# `torchrun --nproc_per_node=N` locally on one VM and doesn't need VNet peering, cross-node
# latency, or a second NIC. Do not add multi-node logic here; if a real cross-node experiment
# is needed later, build a separate module rather than growing this one.
#
# Referenced (not created) resource group: "IncidentFox" / eastus — see ../../../docs/AZURE.md
# for the account facts (subscription id, RG, region, credential policy) this file assumes.
#
# GPU quota for this subscription is currently 0 for both candidate SKUs:
#   Standard_ND96asr_v4      — ND A100 v4: 8×A100 SXM4 40GB, NVLink + 8×200Gb/s IB HDR
#   Standard_ND96isr_H100_v5 — ND H100 v5: 8×H100 SXM5 80GB, NVLink + InfiniBand
# vm_size is a variable (default ND A100 v4) specifically because we don't yet know which
# family the pending quota ticket will approve.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "subscription_id" {
  type        = string
  default     = "27ad7138-6e41-4554-9d72-36eb4502b0bb" # "Azure subscription 1" — docs/AZURE.md
  description = "Pinned explicitly (like AWS's aws_profile var) so this never silently deploys into whatever subscription happens to be ambient-active in `az` context."
}

variable "resource_group_name" {
  type        = string
  default     = "IncidentFox"
  description = "Existing RG — referenced via data source, never created/destroyed by this module."
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Informational default for tfvars/scripts. Resources actually deploy into data.azurerm_resource_group.this.location so they can never drift from where the RG really lives."
}

variable "project" {
  type    = string
  default = "ictd"
}

variable "vm_size" {
  type        = string
  default     = "Standard_ND96asr_v4" # ND A100 v4: 8×A100 SXM4 40GB, NVLink + 8×200Gb/s IB HDR.
  description = <<-EOT
    GPU VM size. Alternative: "Standard_ND96isr_H100_v5" (ND H100 v5, 8×H100 SXM5 80GB,
    NVLink + InfiniBand). Quota for BOTH families is currently 0 in this subscription —
    set this to whichever one the pending quota ticket actually approves. Do not hardcode
    a size anywhere else in this module; everything downstream reads this variable.
  EOT
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to an existing SSH public key (e.g. ~/.ssh/id_ed25519.pub). Required — no default, mirrors AWS's required key_name var. Password auth is disabled."
}

variable "allowed_ssh_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"] # narrow this in terraform.tfvars before applying
  description = "CIDRs allowed to reach port 22. Restrict to your own IP/32 before a real apply — do not leave this open on an expensive GPU box."
}

variable "os_disk_gb" {
  type        = number
  default     = 512 # these workloads pull large HF checkpoints
  description = "OS disk size in GB."
}

variable "os_disk_type" {
  type    = string
  default = "Premium_LRS"
}

# --- VM image ---------------------------------------------------------------
# Ubuntu-HPC marketplace image: ships NVIDIA drivers + CUDA + Mellanox OFED + the NCCL RDMA
# plugin preinstalled for ND/HB-series HPC VMs, which is far more reliable than a bare Ubuntu
# image + manual driver install for a "must run the moment quota lands" requirement.
#
# VERIFIED LIVE 2026-08-17 via `az vm image list-skus --publisher microsoft-dsvm --offer
# ubuntu-hpc --location eastus`. The publisher is "microsoft-dsvm", NOT "Canonical" — an
# earlier draft of this file guessed Canonical (a very reasonable guess, since Canonical does
# publish plain Ubuntu images, just not this HPC-specific one) and would have failed at apply
# time. SKU "2204" confirmed to exist with a build as recent as version 22.04.2026080501.
# "2204-v100"/"2204-rocm"/"2404-gb"/"2404-maia" are GPU-vendor-specific variants (V100/AMD
# ROCm/Grace-Blackwell/Microsoft Maia) — plain "2204" or "2404" is correct for A100/H100-class
# ND-series. Re-run the az command above before applying if this has aged; SKU listings do
# drift, just not as unverified-guess-badly as the publisher name was.

variable "vm_image_publisher" {
  type    = string
  default = "microsoft-dsvm"
}

variable "vm_image_offer" {
  type    = string
  default = "ubuntu-hpc"
}

variable "vm_image_sku" {
  type        = string
  default     = "2204" # confirmed live 2026-08-17, see comment above
  description = "Marketplace SKU string. Verified 2026-08-17 against `az vm image list-skus --publisher microsoft-dsvm --offer ubuntu-hpc --location eastus` — re-check if this has aged."
}

variable "vm_image_version" {
  type    = string
  default = "latest"
}

# --- Spot ---------------------------------------------------------------

variable "use_spot" {
  type    = bool
  default = false
}

variable "spot_max_bid_price" {
  type        = number
  default     = -1 # -1 = cap at current pay-as-you-go price (capacity-eviction only, no price-based eviction)
  description = "Only used when use_spot=true. Set an explicit $/hr ceiling to accept price-based eviction risk for potentially lower cost."
}

variable "spot_eviction_policy" {
  type        = string
  default     = "Delete" # closest analog to AWS's spot_instance_interruption_behavior="terminate"
  description = "Only used when use_spot=true. \"Delete\" fully tears down on eviction (matches AWS's terminate-on-interrupt behavior here); \"Deallocate\" stops compute billing but keeps the disk around."
  validation {
    condition     = contains(["Deallocate", "Delete"], var.spot_eviction_policy)
    error_message = "spot_eviction_policy must be \"Deallocate\" or \"Delete\"."
  }
}

# --- Budget guardrail ---------------------------------------------------------

variable "budget_usd" {
  type        = number
  default     = 250
  description = "Monthly spend alert threshold (80%) for the referenced resource group."
}

variable "budget_email" {
  type    = string
  default = "" # empty disables the budget resource entirely
}

variable "budget_start_date" {
  type        = string
  default     = "2026-09-01T00:00:00Z" # must be the 1st of a month, RFC3339
  description = "azurerm_consumption_budget_resource_group requires the 1st-of-month start. Schema (time_period required, start_date/end_date RFC3339) verified 2026-08-17 against hashicorp/terraform-provider-azurerm's current docs — this file's notification block (operator/threshold/contact_emails) matches that schema correctly."
}

variable "budget_end_date" {
  type        = string
  default     = "2034-09-01T00:00:00Z" # far-future placeholder — 8 years out, within Azure's typical allowed range
  description = "See budget_start_date."
}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

locals {
  tags = { Project = var.project, Purpose = "interconnect-train-detect" }
}

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

resource "azurerm_virtual_network" "this" {
  name                = "${var.project}-vnet"
  address_space       = ["10.43.0.0/16"] # distinct range from the AWS module's 10.42.0.0/16
  location            = data.azurerm_resource_group.this.location
  resource_group_name = data.azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_subnet" "this" {
  name                 = "${var.project}-subnet"
  resource_group_name  = data.azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.43.1.0/24"]
}

# Single VM — no self/inter-node rules needed. run_experiment.py's smoke path binds the
# collector to 127.0.0.1 only, so port 8765 / the torchrun rendezvous range never need to be
# reachable from outside the box. If a future experiment needs them exposed, add rules then.
resource "azurerm_network_security_group" "this" {
  name                = "${var.project}-nsg"
  location            = data.azurerm_resource_group.this.location
  resource_group_name = data.azurerm_resource_group.this.name

  security_rule {
    name                       = "AllowSSHInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefixes    = var.allowed_ssh_cidrs
    destination_address_prefix = "*"
  }

  tags = local.tags
}

resource "azurerm_public_ip" "this" {
  name                = "${var.project}-pip"
  location            = data.azurerm_resource_group.this.location
  resource_group_name = data.azurerm_resource_group.this.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

# Accelerated Networking — required for ND-series to get full network throughput. Cheap to
# enable, no downside for a single node.
resource "azurerm_network_interface" "this" {
  name                           = "${var.project}-nic"
  location                       = data.azurerm_resource_group.this.location
  resource_group_name            = data.azurerm_resource_group.this.name
  accelerated_networking_enabled = true # `enable_accelerated_networking` is deprecated as of azurerm 3.x, removed in 4.x — verified 2026-08-17

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.this.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.this.id
  }

  tags = local.tags
}

resource "azurerm_network_interface_security_group_association" "this" {
  network_interface_id      = azurerm_network_interface.this.id
  network_security_group_id = azurerm_network_security_group.this.id
}

# ---------------------------------------------------------------------------
# VM
# ---------------------------------------------------------------------------

resource "azurerm_linux_virtual_machine" "this" {
  name                  = "${var.project}-vm"
  location              = data.azurerm_resource_group.this.location
  resource_group_name   = data.azurerm_resource_group.this.name
  size                  = var.vm_size
  admin_username        = var.admin_username
  network_interface_ids = [azurerm_network_interface.this.id]

  disable_password_authentication = true
  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.os_disk_type
    disk_size_gb         = var.os_disk_gb
  }

  source_image_reference {
    publisher = var.vm_image_publisher
    offer     = var.vm_image_offer
    sku       = var.vm_image_sku
    version   = var.vm_image_version
  }

  # Minimal, analogous to the AWS module's user_data — just create the working dir and log a
  # boot marker. The real Python stack setup happens over SSH in bootstrap.sh, same division
  # of labor as the AWS scripts.
  custom_data = base64encode(<<-EOF
    #!/bin/bash
    set -euo pipefail
    echo "ICTD azure custom_data $(date -u) size=${var.vm_size}" > /var/log/ictd-custom-data.log
    mkdir -p /home/${var.admin_username}/ictd
    chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/ictd
  EOF
  )

  priority        = var.use_spot ? "Spot" : "Regular"
  eviction_policy = var.use_spot ? var.spot_eviction_policy : null
  max_bid_price   = var.use_spot ? var.spot_max_bid_price : null

  tags = merge(local.tags, { Name = "${var.project}-vm" })

  lifecycle {
    precondition {
      condition     = fileexists(var.ssh_public_key_path)
      error_message = "ssh_public_key_path (${var.ssh_public_key_path}) does not exist — generate a key or point at an existing one before applying."
    }
  }
}

# ---------------------------------------------------------------------------
# Budget guardrail (mirrors AWS's aws_budgets_budget block)
# ---------------------------------------------------------------------------

resource "azurerm_consumption_budget_resource_group" "this" {
  count             = var.budget_email != "" ? 1 : 0
  name              = "${var.project}-monthly"
  resource_group_id = data.azurerm_resource_group.this.id

  amount     = var.budget_usd
  time_grain = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = var.budget_end_date
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    contact_emails = [var.budget_email]
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "vm_id" {
  value = azurerm_linux_virtual_machine.this.id
}
output "public_ip" {
  value = azurerm_public_ip.this.ip_address
}
output "private_ip" {
  value = azurerm_network_interface.this.private_ip_address
}
output "vm_size" {
  value = var.vm_size
}
output "location" {
  value = data.azurerm_resource_group.this.location
}
output "ssh_command" {
  # Assumes the conventional private-key-alongside-public-key naming (id_ed25519 / id_ed25519.pub).
  value = "ssh -i ${replace(var.ssh_public_key_path, ".pub", "")} ${var.admin_username}@${azurerm_public_ip.this.ip_address}"
}
output "collector_url" {
  # Single-node run_experiment.py's smoke path binds the collector to loopback only.
  value = "http://127.0.0.1:8765"
}
output "cost_warning" {
  value = "1× ${var.vm_size} (single VM, no cross-node fabric) — confirm $/hr via infra/azure/scripts/cost.sh; autodestroy.sh recommended"
}
output "spot_enabled" {
  value = var.use_spot
}
