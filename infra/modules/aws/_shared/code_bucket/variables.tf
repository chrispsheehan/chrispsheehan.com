### start of static vars set in root.hcl ###
variable "code_bucket" {
  description = "S3 bucket to host build artifacts"
  type        = string
}
### end of static vars set in root.hcl ###

variable "lambda_artifact_dir" {
  description = "Top-level S3 prefix used for Lambda zip artifacts"
  type        = string
  default     = "lambdas"
}

variable "appspec_artifact_dir" {
  description = "Top-level S3 prefix used for AppSpec deployment artifacts"
  type        = string
  default     = "appspec"
}

variable "frontend_artifact_dir" {
  description = "Top-level S3 prefix used for frontend build artifacts"
  type        = string
  default     = "frontend"
}

variable "lambda_bootstrap_zip_key" {
  description = "S3 object key used for the shared Lambda bootstrap zip"
  type        = string
}

variable "code_artifact_expiration_days" {
  description = "Number of days before deployable code artifacts are deleted (set to 0 to disable)"
  type        = number
  default     = 0
}
