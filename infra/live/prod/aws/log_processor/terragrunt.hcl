include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependencies {
  paths = [
    "../frontend",
    "../oidc",
    "../security",
    "../s3_database",
  ]
}

dependency "frontend" {
  config_path = "../frontend"

  mock_outputs = {
    cloudfront_logs_bucket_name = "chrispsheehan.com.logs"
    cloudfront_logs_bucket_arn  = "arn:aws:s3:::chrispsheehan.com.logs"
    cloudfront_logs_prefix      = "cloudfront-logs/"
    reports_bucket_name         = "prod-chrispsheehan-com-reports"
    reports_bucket_arn          = "arn:aws:s3:::prod-chrispsheehan-com-reports"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

dependency "security" {
  config_path = "../security"

  mock_outputs = {
    runtime_security_group_id = "sg-00000000000000000"
    vpc_id                    = "vpc-00000000000000000"
    private_subnet_ids        = ["subnet-00000000000000000", "subnet-11111111111111111"]
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

dependency "s3_database" {
  config_path = "../s3_database"

  mock_outputs = {
    bucket_name = "prod-chrispsheehan-com-database"
    bucket_arn  = "arn:aws:s3:::prod-chrispsheehan-com-database"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

terraform {
  source = "../../../../modules//aws//log_processor"
}

inputs = {
  runtime_security_group_id = dependency.security.outputs.runtime_security_group_id
  private_subnet_ids        = dependency.security.outputs.private_subnet_ids
  report_bucket_name        = dependency.frontend.outputs.reports_bucket_name
  report_bucket_arn         = dependency.frontend.outputs.reports_bucket_arn
  database_bucket_name      = dependency.s3_database.outputs.bucket_name
  database_bucket_arn       = dependency.s3_database.outputs.bucket_arn
  logs_bucket_name          = dependency.frontend.outputs.cloudfront_logs_bucket_name
  logs_bucket_arn           = dependency.frontend.outputs.cloudfront_logs_bucket_arn
  logs_bucket_prefix        = dependency.frontend.outputs.cloudfront_logs_prefix
}
