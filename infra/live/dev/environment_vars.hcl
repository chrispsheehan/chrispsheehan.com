locals {
  deploy_branches          = ["*"]
  force_delete             = true
  force_destroy_db         = true
  domain_prefix            = "wip.dev"
  vpc_name                 = "vpc"
  logs_bucket_name         = "chrispsheehan.com.logs"
  logs_bucket_arn          = "arn:aws:s3:::chrispsheehan.com.logs"
  logs_bucket_prefix       = ""
  logs_processor_max_files = 10
}

inputs = {
  deploy_branches          = local.deploy_branches
  force_delete             = local.force_delete
  force_destroy_db         = local.force_destroy_db
  domain_prefix            = local.domain_prefix
  vpc_name                 = local.vpc_name
  logs_bucket_name         = local.logs_bucket_name
  logs_bucket_arn          = local.logs_bucket_arn
  logs_bucket_prefix       = local.logs_bucket_prefix
  logs_processor_max_files = local.logs_processor_max_files
}
