locals {
  aws_region       = "eu-west-2"
  hosted_zone_name = "chrispsheehan.com"
  allowed_role_actions = [
    "acm:*",
    "cloudfront:*",
    "iam:*",
    "lambda:*",
    "logs:*",
    "route53:*",
    "s3:*",
    "codedeploy:*",
    "dynamodb:*",
    "ec2:*",
    "events:*",
  ]
  code_artifact_expiration_days = 0
}

inputs = {
  aws_region                    = local.aws_region
  hosted_zone_name              = local.hosted_zone_name
  allowed_role_actions          = local.allowed_role_actions
  code_artifact_expiration_days = local.code_artifact_expiration_days
}
