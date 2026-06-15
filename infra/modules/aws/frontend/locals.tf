locals {
  name                  = "${var.environment}-${replace(var.project_name, ".", "-")}"
  bucket_name           = "${data.aws_caller_identity.current.account_id}-${local.name}-frontend"
  root_file             = "index.html"
  domain_name           = trimsuffix(var.domain_name, ".")
  cloudfront_origin_id  = "s3-${local.bucket_name}"
  managed_cache_policy  = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  managed_origin_policy = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
}
