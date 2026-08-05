# ICTD AWS cluster — EFA behavior branches on instance family.
#
# g5.*  → efa_extra_nics forced 0 (no EFA ENI attach)
# p4d.* / p5.* → default efa_extra_nics=3 (override in tfvars)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "aws_profile" {
  type    = string
  default = "default"
}
variable "project" {
  type    = string
  default = "ictd"
}
variable "key_name" {
  type = string
}
variable "instance_type" {
  type    = string
  default = "g5.48xlarge"
}
variable "ami_id" {
  type    = string
  default = ""
}
variable "use_spot" {
  type    = bool
  default = false
}
variable "spot_max_price" {
  type    = string
  default = ""
}
variable "volume_gb" {
  type    = number
  default = 256
}
variable "allowed_ssh_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}
variable "efa_extra_nics" {
  type        = number
  default     = -1
  description = "-1 = auto (0 for g5, 3 for p4d/p5). Explicit ≥0 overrides."
}
variable "budget_usd" {
  type        = number
  default     = 250
  description = "AWS Budgets alert threshold for this account/project tag filter (monthly)."
}
variable "budget_email" {
  type    = string
  default = ""
}

data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_caller_identity" "current" {}

data "aws_ami" "dlami" {
  count       = var.ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.* (Ubuntu 22.04)*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

locals {
  ami    = var.ami_id != "" ? var.ami_id : data.aws_ami.dlami[0].id
  tags   = { Project = var.project, Purpose = "interconnect-train-detect" }
  family = split(".", var.instance_type)[0]
  efa_nics = var.efa_extra_nics >= 0 ? var.efa_extra_nics : (
    contains(["p4d", "p4de", "p5", "p5e", "p5en"], local.family) ? 3 : 0
  )
  efa_supported = local.efa_nics > 0 || contains(["p4d", "p4de", "p5", "p5e", "p5en", "g5", "g6", "gr6"], local.family)
}

resource "aws_vpc" "this" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = "${var.project}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = local.tags
}

resource "aws_subnet" "this" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.42.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags                    = merge(local.tags, { Name = "${var.project}-subnet" })
}

resource "aws_route_table" "this" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = local.tags
}

resource "aws_route_table_association" "this" {
  subnet_id      = aws_subnet.this.id
  route_table_id = aws_route_table.this.id
}

resource "aws_security_group" "this" {
  name   = "${var.project}-sg"
  vpc_id = aws_vpc.this.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }
  ingress {
    from_port = 8765
    to_port   = 8765
    protocol  = "tcp"
    self      = true
  }
  ingress {
    from_port = 29500
    to_port   = 29600
    protocol  = "tcp"
    self      = true
  }
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_placement_group" "cluster" {
  name     = "${var.project}-pg"
  strategy = "cluster"
  tags     = local.tags
}

# Least-privilege node role: SSM + read pricing optional via separate user key
resource "aws_iam_role" "node" {
  name = "${var.project}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "node_minimal" {
  name = "${var.project}-node-minimal"
  role = aws_iam_role.node.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSM"
        Effect = "Allow"
        Action = [
          "ssmmessages:*", "ssm:UpdateInstanceInformation", "ec2messages:*"
        ]
        Resource = "*"
      },
      {
        Sid      = "SelfDescribe"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:DescribeTags"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "node" {
  name = "${var.project}-node-profile"
  role = aws_iam_role.node.name
}

resource "aws_instance" "node" {
  count                       = 2
  ami                         = local.ami
  instance_type               = var.instance_type
  key_name                    = var.key_name
  subnet_id                   = aws_subnet.this.id
  vpc_security_group_ids      = [aws_security_group.this.id]
  iam_instance_profile        = aws_iam_instance_profile.node.name
  placement_group             = aws_placement_group.cluster.id
  associate_public_ip_address = true
  ebs_optimized               = true

  root_block_device {
    volume_size = var.volume_gb
    volume_type = "gp3"
  }

  metadata_options { http_tokens = "required" }

  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail
    echo "ICTD userdata $(date -u) family=${local.family} efa_nics=${local.efa_nics}" > /var/log/ictd-userdata.log
    mkdir -p /home/ubuntu/ictd && chown ubuntu:ubuntu /home/ubuntu/ictd
  EOF

  dynamic "instance_market_options" {
    for_each = var.use_spot ? [1] : []
    content {
      market_type = "spot"
      spot_options {
        spot_instance_type             = "one-time"
        instance_interruption_behavior = "terminate"
        max_price                      = var.spot_max_price != "" ? var.spot_max_price : null
      }
    }
  }

  tags = merge(local.tags, {
    Name = "${var.project}-node${count.index}"
    Rank = tostring(count.index)
  })

  lifecycle {
    precondition {
      condition     = local.family != "p4d" || local.efa_nics >= 1
      error_message = "p4d requires efa_extra_nics>=1 (auto=3). For software-only use g5.48xlarge."
    }
  }
}

resource "aws_network_interface" "efa" {
  count           = 2 * local.efa_nics
  subnet_id       = aws_subnet.this.id
  security_groups = [aws_security_group.this.id]
  interface_type  = "efa"
  tags            = merge(local.tags, { Name = "${var.project}-efa-${count.index}" })
}

resource "aws_network_interface_attachment" "efa" {
  count                = 2 * local.efa_nics
  instance_id          = aws_instance.node[floor(count.index / max(local.efa_nics, 1))].id
  network_interface_id = aws_network_interface.efa[count.index].id
  device_index         = (count.index % max(local.efa_nics, 1)) + 1
}

# Monthly budget alert (account-level when email set — tag filters are flaky across accounts)
resource "aws_budgets_budget" "ictd" {
  count        = var.budget_email != "" ? 1 : 0
  name         = "${var.project}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }
}

output "instance_ids" {
  value = aws_instance.node[*].id
}
output "public_ips" {
  value = aws_instance.node[*].public_ip
}
output "private_ips" {
  value = aws_instance.node[*].private_ip
}
output "master_addr" {
  value = aws_instance.node[0].private_ip
}
output "collector_url" {
  value = "http://${aws_instance.node[0].private_ip}:8765"
}
output "efa_extra_nics" {
  value = local.efa_nics
}
output "instance_family" {
  value = local.family
}
output "ssh_node0" {
  value = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.node[0].public_ip}"
}
output "ssh_node1" {
  value = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.node[1].public_ip}"
}
output "cost_warning" {
  value = "2× ${var.instance_type} efa_nics=${local.efa_nics} — confirm $/hr; autodestroy.sh recommended"
}
output "spot_enabled" {
  value = var.use_spot
}
