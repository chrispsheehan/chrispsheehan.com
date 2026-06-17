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

variable "logs_bucket_name" {
  type    = string
  default = null
}

variable "logs_bucket_arn" {
  type    = string
  default = null
}

variable "logs_bucket_prefix" {
  type    = string
  default = "cloudfront-logs/"
}

variable "processed_log_files_table_name" {
  type = string
}

variable "processed_log_files_table_arn" {
  type = string
}

variable "log_retention_days" {
  type    = number
  default = 1
}
