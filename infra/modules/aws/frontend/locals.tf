locals {
  name                  = "${var.environment}-${replace(var.project_name, ".", "-")}"
  domain_name           = "${trimsuffix(var.domain_prefix, ".")}.${trimsuffix(var.hosted_zone_name, ".")}"
  bucket_name           = local.domain_name
  logs_bucket_name      = "${local.domain_name}.logs"
  logs_prefix           = "cloudfront-logs/"
  root_file             = "index.html"
  cloudfront_origin_id  = "s3-${replace(local.bucket_name, ".", "-")}"
  data_origin_id        = "s3-${var.data_bucket_name}"
  managed_cache_policy  = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  managed_origin_policy = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
}
