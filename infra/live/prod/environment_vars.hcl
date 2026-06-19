locals {
  log_retention_days = 14
  deploy_branches    = ["main"]
  vpc_name           = "vpc"
}

inputs = {
  log_retention_days = local.log_retention_days
  deploy_branches    = local.deploy_branches
  vpc_name           = local.vpc_name
}
