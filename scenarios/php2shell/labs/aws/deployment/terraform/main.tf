provider "aws" {
  profile = var.profile != "" ? var.profile : null
  region  = var.region
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "al2023_arm64" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.1-arm64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

locals {
  method = "terraform"
  tags = {
    VulHarnessProject          = "VulHarness"
    VulHarnessScenario         = "php2shell"
    VulHarnessEnvironment      = "aws-ec2"
    VulHarnessDeployment       = var.deployment_id
    VulHarnessManagedBy        = local.method
    VulHarnessDeploymentMethod = local.method
    VulHarnessOwner            = var.owner
    VulHarnessExpires          = var.expires_at
  }
}

resource "aws_vpc" "lab" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(local.tags, {
    VulHarnessResource = "vpc"
    Name               = "vulharness-php2shell-terraform-${var.deployment_id}-vpc"
  })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.lab.id
  cidr_block              = var.subnet_cidr
  availability_zone       = var.availability_zone != "" ? var.availability_zone : data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags = merge(local.tags, {
    VulHarnessResource = "public-subnet"
    Name               = "vulharness-php2shell-terraform-${var.deployment_id}-public"
  })
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
  tags = merge(local.tags, {
    VulHarnessResource = "internet-gateway"
    Name               = "vulharness-php2shell-terraform-${var.deployment_id}-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
  tags = merge(local.tags, {
    VulHarnessResource = "route-table"
    Name               = "vulharness-php2shell-terraform-${var.deployment_id}-public-route"
  })
}

resource "aws_route" "default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "lab" {
  name        = "vulharness-php2shell-terraform-${var.deployment_id}"
  description = "VulHarness PHP2Shell Terraform lab with no inbound access"
  vpc_id      = aws_vpc.lab.id

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    VulHarnessResource = "security-group"
    Name               = "vulharness-php2shell-terraform-${var.deployment_id}-sg"
  })
}

resource "aws_iam_role" "lab" {
  name = "vh-php2shell-terraform-${var.deployment_id}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = merge(local.tags, {
    VulHarnessResource = "iam-role"
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.lab.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "lab" {
  name = "vh-php2shell-terraform-${var.deployment_id}-profile"
  role = aws_iam_role.lab.name
  tags = merge(local.tags, {
    VulHarnessResource = "instance-profile"
  })
}

resource "aws_launch_template" "lab_c" {
  name_prefix   = "vulharness-php2shell-terraform-lab-c-${var.deployment_id}-"
  image_id      = data.aws_ami.al2023_arm64.id
  instance_type = "t4g.small"
  iam_instance_profile {
    name = aws_iam_instance_profile.lab.name
  }
  network_interfaces {
    subnet_id                   = aws_subnet.public.id
    security_groups             = [aws_security_group.lab.id]
    associate_public_ip_address = true
  }
  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "disabled"
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }
  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.tags, { VulHarnessResource = "instance", VulHarnessLab = "lab-c", Name = "vulharness-php2shell-terraform-lab-c-${var.deployment_id}" })
  }
  tag_specifications {
    resource_type = "volume"
    tags          = merge(local.tags, { VulHarnessResource = "volume", VulHarnessLab = "lab-c", Name = "vulharness-php2shell-terraform-lab-c-${var.deployment_id}-root" })
  }
}

resource "aws_launch_template" "lab_d" {
  name_prefix   = "vulharness-php2shell-terraform-lab-d-${var.deployment_id}-"
  image_id      = data.aws_ami.al2023_arm64.id
  instance_type = "t4g.small"
  iam_instance_profile {
    name = aws_iam_instance_profile.lab.name
  }
  network_interfaces {
    subnet_id                   = aws_subnet.public.id
    security_groups             = [aws_security_group.lab.id]
    associate_public_ip_address = true
  }
  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "disabled"
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }
  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.tags, { VulHarnessResource = "instance", VulHarnessLab = "lab-d", Name = "vulharness-php2shell-terraform-lab-d-${var.deployment_id}" })
  }
  tag_specifications {
    resource_type = "volume"
    tags          = merge(local.tags, { VulHarnessResource = "volume", VulHarnessLab = "lab-d", Name = "vulharness-php2shell-terraform-lab-d-${var.deployment_id}-root" })
  }
}

resource "aws_instance" "lab_c" {
  launch_template {
    id      = aws_launch_template.lab_c.id
    version = aws_launch_template.lab_c.latest_version
  }
  tags = merge(local.tags, { VulHarnessResource = "instance", VulHarnessLab = "lab-c", Name = "vulharness-php2shell-terraform-lab-c-${var.deployment_id}" })
}

resource "aws_instance" "lab_d" {
  launch_template {
    id      = aws_launch_template.lab_d.id
    version = aws_launch_template.lab_d.latest_version
  }
  tags = merge(local.tags, { VulHarnessResource = "instance", VulHarnessLab = "lab-d", Name = "vulharness-php2shell-terraform-lab-d-${var.deployment_id}" })
}
