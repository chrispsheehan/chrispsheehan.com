locals {
  name                 = "${var.environment}-${var.project_name}"
  bucket_name          = "${data.aws_caller_identity.current.account_id}-${local.name}"
  frontend_domain_name = var.frontend_domain_name != "" ? var.frontend_domain_name : "${var.project_name}.${var.environment}.${var.domain_name}"
  hosted_zone_name     = var.frontend_hosted_zone_name != "" ? trimsuffix(var.frontend_hosted_zone_name, ".") : var.domain_name

  s3_origin_id = "s3"

  root_file                  = "index.html"
  caching_optimized_id       = "Managed-CachingOptimized"
  origin_request_policy_id   = "Managed-CORS-S3Origin"
  response_headers_policy_id = "Managed-CORS-With-Preflight"
}
