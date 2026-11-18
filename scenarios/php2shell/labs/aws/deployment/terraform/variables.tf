variable "profile" {
  type        = string
  description = "AWS shared-config profile used for this deployment."
  default     = ""
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "deployment_id" {
  type        = string
  description = "Unique deployment identity."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,31}$", var.deployment_id))
    error_message = "deployment_id must contain only lowercase letters, digits and hyphens."
  }
}

variable "expires_at" {
  type        = string
  description = "UTC expiration metadata."
  validation {
    condition     = can(regex("^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.expires_at))
    error_message = "expires_at must be an ISO-8601 UTC timestamp."
  }
}

variable "owner" {
  type    = string
  default = "workshop"
}

variable "vpc_cidr" {
  type    = string
  default = "10.252.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.252.1.0/24"
}

variable "availability_zone" {
  type    = string
  default = ""
}
