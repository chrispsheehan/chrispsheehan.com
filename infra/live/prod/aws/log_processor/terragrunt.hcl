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
    bucket_name                        = "prod-placeholder-report-bucket"
    bucket_arn                         = "arn:aws:s3:::prod-placeholder-report-bucket"
    processed_log_files_table_name     = "prod-placeholder-processed-log-files"
    processed_log_files_table_arn      = "arn:aws:dynamodb:eu-west-2:000000000000:table/prod-placeholder-processed-log-files"
    processed_log_files_table_region   = "eu-west-2"
    processed_log_files_table_endpoint = "https://dynamodb.eu-west-2.amazonaws.com"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

terraform {
  source = "../../../../modules//aws//log_processor"
}

inputs = {
  runtime_security_group_id      = dependency.security.outputs.runtime_security_group_id
  private_subnet_ids             = dependency.security.outputs.private_subnet_ids
  report_bucket_name             = dependency.s3_database.outputs.bucket_name
  report_bucket_arn              = dependency.s3_database.outputs.bucket_arn
  processed_log_files_table_name = dependency.s3_database.outputs.processed_log_files_table_name
  processed_log_files_table_arn  = dependency.s3_database.outputs.processed_log_files_table_arn
  dynamodb_aws_region            = dependency.s3_database.outputs.processed_log_files_table_region
  dynamodb_endpoint              = dependency.s3_database.outputs.processed_log_files_table_endpoint
}
