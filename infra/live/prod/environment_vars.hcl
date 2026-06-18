locals {
  log_retention_days = 14
  deploy_branches    = ["main"]
  domain_prefix      = "wip"
  vpc_name           = "vpc"
}

inputs = {
  log_retention_days = local.log_retention_days
  deploy_branches    = local.deploy_branches
  domain_prefix      = local.domain_prefix
  vpc_name           = local.vpc_name
}
