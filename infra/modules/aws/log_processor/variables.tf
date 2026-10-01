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

variable "bootstrap_zip_key" {
  type = string
}

variable "report_bucket_name" {
  type = string
}

variable "report_bucket_arn" {
  type = string
}

variable "database_bucket_name" {
  type = string
}

variable "database_bucket_arn" {
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

variable "database_read_workers" {
  type        = number
  description = "Maximum concurrent S3 reads while rebuilding the visit summary."
  default     = 8

  validation {
    condition     = var.database_read_workers >= 1 && floor(var.database_read_workers) == var.database_read_workers
    error_message = "database_read_workers must be a positive integer."
  }
}

variable "memory_size" {
  type        = number
  description = "Lambda memory in MB; additional memory also increases CPU and network allocation."
  default     = 512

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240 && floor(var.memory_size) == var.memory_size
    error_message = "memory_size must be an integer from 128 through 10240."
  }
}

variable "sqs_batch_size" {
  type        = number
  description = "Maximum number of S3 object notifications processed per Lambda invocation."
  default     = 25

  validation {
    condition     = var.sqs_batch_size >= 1 && var.sqs_batch_size <= 10000 && floor(var.sqs_batch_size) == var.sqs_batch_size
    error_message = "sqs_batch_size must be an integer from 1 through 10000."
  }
}

variable "sqs_batch_window_seconds" {
  type        = number
  description = "Maximum time Lambda waits to collect an SQS batch."
  default     = 60

  validation {
    condition     = var.sqs_batch_window_seconds >= 1 && var.sqs_batch_window_seconds <= 300 && floor(var.sqs_batch_window_seconds) == var.sqs_batch_window_seconds
    error_message = "sqs_batch_window_seconds must be an integer from 1 through 300."
  }
}

variable "sqs_consumer_enabled" {
  type        = bool
  description = "Whether the Lambda event source mapping consumes messages from the ingestion queue."
  default     = true
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum runtime in seconds for the log processor Lambda."
  default     = 300

  validation {
    condition     = var.timeout_seconds >= 1 && var.timeout_seconds <= 900 && floor(var.timeout_seconds) == var.timeout_seconds
    error_message = "timeout_seconds must be an integer from 1 through 900."
  }
}

variable "log_retention_days" {
  type    = number
  default = 1
}
