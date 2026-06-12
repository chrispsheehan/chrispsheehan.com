locals {
  vpc_name   = "vpc"
  aws_region = "eu-west-2"
  allowed_role_actions = [
    "s3:*",
    "iam:*",
    "cloudfront:*",
    "acm:*",
    "route53:*",
  ]
  code_artifact_expiration_days = 0
}

inputs = {
  vpc_name                      = local.vpc_name
  aws_region                    = local.aws_region
  allowed_role_actions          = local.allowed_role_actions
  code_artifact_expiration_days = local.code_artifact_expiration_days
}
