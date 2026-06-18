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
  type = string
}

variable "logs_bucket_arn" {
  type = string
}

variable "logs_bucket_prefix" {
  type    = string
  default = "cloudfront-logs/"
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

variable "processed_log_files_table_name" {
  type = string
}

variable "processed_log_files_table_arn" {
  type = string
}

variable "dynamodb_aws_region" {
  type        = string
  description = "AWS region for the processed log files DynamoDB table."
}

variable "dynamodb_endpoint" {
  type        = string
  description = "Endpoint URL for the processed log files DynamoDB table."
}

variable "log_level" {
  type        = string
  description = "Python log level for the log processor Lambda."
  default     = "INFO"

  validation {
    condition = contains(
      ["CRITICAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"],
      upper(var.log_level),
    )
    error_message = "log_level must be one of CRITICAL, ERROR, WARNING, WARN, INFO, DEBUG, or NOTSET."
  }
}

variable "logs_processor_max_files" {
  type        = number
  description = "Optional maximum number of CloudFront log files to claim per invocation."
  default     = null

  validation {
    condition     = var.logs_processor_max_files == null || var.logs_processor_max_files > 0
    error_message = "logs_processor_max_files must be null or a positive number."
  }
}

variable "log_retention_days" {
  type    = number
  default = 1
}
