### start of static vars set in root.hcl ###
variable "project_name" {
  type        = string
  description = "Project name used in naming resources"
}

variable "environment" {
  type        = string
  description = "Environment reference used in naming resources i.e. 'dev'"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "state_bucket" {
  type        = string
  description = "S3 bucket used for Terraform remote state"
}

variable "deploy_role_arn" {
  type        = string
  description = "ARN of the OIDC deploy role to grant frontend bucket access"
}
### end of static vars set in root.hcl ###

variable "hosted_zone_name" {
  type        = string
  description = "Existing public Route53 hosted zone name"
}

variable "domain_prefix" {
  type        = string
  description = "Frontend DNS label prefix inside hosted_zone_name"
}

variable "data_bucket_name" {
  type        = string
  description = "S3 bucket name for data objects served under /data/*"
}

variable "data_bucket_arn" {
  type        = string
  description = "S3 bucket ARN for data objects served under /data/*"
}

variable "data_bucket_regional_domain_name" {
  type        = string
  description = "Regional S3 domain name for the data bucket CloudFront origin"
}

variable "log_retention_days" {
  type        = number
  description = "Number of days to retain CloudFront standard logs"
  default     = 14

  validation {
    condition     = var.log_retention_days > 0
    error_message = "log_retention_days must be a positive number."
  }
}
