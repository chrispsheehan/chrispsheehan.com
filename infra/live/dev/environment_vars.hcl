locals {
  deploy_branches = ["*"]
  force_delete    = true
  domain_name     = "wip.chrispsheehan.com"
}

inputs = {
  deploy_branches = local.deploy_branches
  force_delete    = local.force_delete
  domain_name     = local.domain_name
}
