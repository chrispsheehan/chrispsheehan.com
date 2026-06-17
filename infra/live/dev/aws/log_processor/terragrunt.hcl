include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependencies {
  paths = [
    "../oidc",
    "../security",
    "../s3_database",
  ]
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
    bucket_name                    = "dev-placeholder-report-bucket"
    bucket_arn                     = "arn:aws:s3:::dev-placeholder-report-bucket"
    processed_log_files_table_name = "dev-placeholder-processed-log-files"
    processed_log_files_table_arn  = "arn:aws:dynamodb:eu-west-2:000000000000:table/dev-placeholder-processed-log-files"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

terraform {
  source = "../../../../modules//aws//log_processor"
}

inputs = {
  logs_bucket_name               = dependency.s3_database.outputs.bucket_name
  logs_bucket_arn                = dependency.s3_database.outputs.bucket_arn
  runtime_security_group_id      = dependency.security.outputs.runtime_security_group_id
  private_subnet_ids             = dependency.security.outputs.private_subnet_ids
  report_bucket_name             = dependency.s3_database.outputs.bucket_name
  report_bucket_arn              = dependency.s3_database.outputs.bucket_arn
  processed_log_files_table_name = dependency.s3_database.outputs.processed_log_files_table_name
  processed_log_files_table_arn  = dependency.s3_database.outputs.processed_log_files_table_arn
}
