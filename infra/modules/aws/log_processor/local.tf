locals {
  lambda_runtime            = "python3.12"
  lambda_handler            = "lambda_handler.lambda_handler"
  compute_platform          = "Lambda"
  lambda_bootstrap_zip_key  = "bootstrap/bootstrap-lambda.zip"
  lambda_name               = "${var.environment}-${replace(var.project_name, ".", "-")}-log-processor"
  deployment_config_name    = "${local.lambda_name}-deploy-allatonce"
  daily_schedule_expression = "cron(0 0 * * ? *)"
  logs_bucket_name          = coalesce(var.logs_bucket_name, var.report_bucket_name)
  logs_bucket_arn           = coalesce(var.logs_bucket_arn, var.report_bucket_arn)
}
