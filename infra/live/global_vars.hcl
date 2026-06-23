locals {
  aws_region               = "eu-west-2"
  hosted_zone_name         = "chrispsheehan.com"
  lambda_bootstrap_zip_key = "bootstrap/bootstrap-lambda.zip"
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
  lambda_bootstrap_zip_key      = local.lambda_bootstrap_zip_key
  allowed_role_actions          = local.allowed_role_actions
  code_artifact_expiration_days = local.code_artifact_expiration_days
}
