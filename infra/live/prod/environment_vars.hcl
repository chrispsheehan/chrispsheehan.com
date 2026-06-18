locals {
  log_retention_days = 14
  deploy_branches    = ["main"]
  domain_prefix      = "wip"
  vpc_name           = "vpc"
  logs_bucket_name   = "chrispsheehan.com.logs"
  logs_bucket_arn    = "arn:aws:s3:::chrispsheehan.com.logs"
  logs_bucket_prefix = ""
}

inputs = {
  log_retention_days = local.log_retention_days
  deploy_branches    = local.deploy_branches
  domain_prefix      = local.domain_prefix
  vpc_name           = local.vpc_name
  logs_bucket_name   = local.logs_bucket_name
  logs_bucket_arn    = local.logs_bucket_arn
  logs_bucket_prefix = local.logs_bucket_prefix
}
