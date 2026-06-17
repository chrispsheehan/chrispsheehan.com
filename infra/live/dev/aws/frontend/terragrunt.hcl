include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependencies {
  paths = [
    "../oidc",
    "../s3_database",
  ]
}

dependency "s3_database" {
  config_path = "../s3_database"

  mock_outputs = {
    bucket_name                 = "dev-placeholder-report-bucket"
    bucket_arn                  = "arn:aws:s3:::dev-placeholder-report-bucket"
    bucket_regional_domain_name = "dev-placeholder-report-bucket.s3.eu-west-2.amazonaws.com"
  }

  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "destroy", "init", "show", "graph-dependencies", "output-module-groups"]
}

terraform {
  source = "../../../../modules//aws//frontend"
}

inputs = {
  data_bucket_name                 = dependency.s3_database.outputs.bucket_name
  data_bucket_arn                  = dependency.s3_database.outputs.bucket_arn
  data_bucket_regional_domain_name = dependency.s3_database.outputs.bucket_regional_domain_name
}
