variable "state_bucket" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "code_bucket" {
  type = string
}

variable "report_bucket_name" {
  type = string
}

variable "report_bucket_arn" {
  type = string
}

variable "vpc_name" {
  type        = string
  description = "Name tag of the VPC associated with runtime security resources."
  default     = null
}

variable "runtime_security_group_id" {
  type        = string
  description = "Runtime security group ID from the security stack."
  default     = null
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs from the security stack."
  default     = []
}

variable "log_retention_days" {
  type    = number
  default = 1
}
