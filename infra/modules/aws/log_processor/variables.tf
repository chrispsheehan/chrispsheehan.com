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

variable "log_retention_days" {
  type    = number
  default = 1
}

variable "vpc_name" {
  type = string
}

variable "runtime_security_group_id" {
  type = string
}
