locals {
  deploy_branches = ["*"]
  force_delete    = true
  domain_prefix   = "wip.dev"
}

inputs = {
  deploy_branches = local.deploy_branches
  force_delete    = local.force_delete
  domain_prefix   = local.domain_prefix
}
