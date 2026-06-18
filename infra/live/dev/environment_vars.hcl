locals {
  deploy_branches          = ["*"]
  force_delete             = true
  force_destroy_db         = true
  domain_prefix            = "wip.dev"
  vpc_name                 = "vpc"
  logs_processor_max_files = 10
}

inputs = {
  deploy_branches          = local.deploy_branches
  force_delete             = local.force_delete
  force_destroy_db         = local.force_destroy_db
  domain_prefix            = local.domain_prefix
  vpc_name                 = local.vpc_name
  logs_processor_max_files = local.logs_processor_max_files
}
