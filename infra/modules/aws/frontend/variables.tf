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

variable "domain_name" {
  type        = string
  description = "Base hosted zone domain used to derive the deployed frontend URL"

  validation {
    condition     = length(trimspace(var.domain_name)) > 0
    error_message = "domain_name must be specified."
  }
}

variable "frontend_hosted_zone_name" {
  type        = string
  description = "Optional Route53 hosted zone name for the frontend custom domain"
  default     = ""
}

variable "frontend_domain_name" {
  type        = string
  description = "Optional exact frontend domain name. Defaults to <project_name>.<environment>.<domain_name>."
  default     = ""
}
