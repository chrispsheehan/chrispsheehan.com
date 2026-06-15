locals {
  log_retention_days = 14
  deploy_branches    = ["main"]
  domain_name        = "chrispsheehan.com"
}

inputs = {
  log_retention_days = local.log_retention_days
  deploy_branches    = local.deploy_branches
  domain_name        = local.domain_name
}
