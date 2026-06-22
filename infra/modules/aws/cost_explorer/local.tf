locals {
  lambda_runtime            = "python3.12"
  lambda_handler            = "lambda_handler.lambda_handler"
  compute_platform          = "Lambda"
  lambda_bootstrap_zip_key  = "bootstrap/cost-explorer/bootstrap-lambda.zip"
  lambda_name               = "${var.environment}-${replace(var.project_name, ".", "-")}-cost-explorer"
  deployment_config_name    = "${local.lambda_name}-deploy-allatonce"
  daily_schedule_expression = "cron(0 0 * * ? *)"
}
