include "root" {
  path = find_in_parent_folders("root.hcl")
}

locals {
  allowed_role_actions = [
    "s3:*",
    "iam:*",
    "lambda:*",
    "logs:*",
    "codedeploy:*",
  ]
}

inputs = {
  allowed_role_actions = local.allowed_role_actions
}

terraform {
  source = "tfr:///chrispsheehan/github-oidc-role/aws?version=1.0.1"
}
