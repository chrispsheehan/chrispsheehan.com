include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependencies {
  paths = ["../oidc"]
}

dependency "s3_database" {
  config_path = "../s3_database"

  mock_outputs = {
    bucket_name = "dev-placeholder-report-bucket"
    bucket_arn  = "arn:aws:s3:::dev-placeholder-report-bucket"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

terraform {
  source = "../../../../modules//aws//log_processor"
}

inputs = {
  report_bucket_name = dependency.s3_database.outputs.bucket_name
  report_bucket_arn  = dependency.s3_database.outputs.bucket_arn
}
