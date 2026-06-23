resource "aws_iam_role" "iam_for_lambda" {
  name               = "${local.lambda_name}-iam"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_policy" "lambda_cloudwatch_logs" {
  name   = "${local.lambda_name}-logs"
  policy = data.aws_iam_policy_document.lambda_cloudwatch_logs.json
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_logs.arn
}

resource "aws_iam_policy" "lambda_report_bucket" {
  name   = "${local.lambda_name}-report-bucket"
  policy = data.aws_iam_policy_document.lambda_report_bucket.json
}

resource "aws_iam_role_policy_attachment" "lambda_report_bucket" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_report_bucket.arn
}

resource "aws_iam_policy" "lambda_cost_explorer" {
  name   = "${local.lambda_name}-cost-explorer"
  policy = data.aws_iam_policy_document.lambda_cost_explorer.json
}

resource "aws_iam_role_policy_attachment" "lambda_cost_explorer" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_cost_explorer.arn
}

resource "aws_lambda_function" "cost_explorer" {
  function_name                  = local.lambda_name
  role                           = aws_iam_role.iam_for_lambda.arn
  handler                        = local.lambda_handler
  runtime                        = local.lambda_runtime
  timeout                        = 120
  reserved_concurrent_executions = 1

  s3_bucket = var.code_bucket
  s3_key    = var.bootstrap_zip_key

  publish = true

  environment {
    variables = {
      REPORT_BUCKET    = var.report_bucket_name
      PROJECT_NAME     = var.project_name
      ENVIRONMENT_NAME = var.environment
    }
  }

  tags = {
    CodeDeployApplication = aws_codedeploy_app.cost_explorer.name
    CodeDeployGroup       = aws_codedeploy_deployment_group.cost_explorer.deployment_group_name
    DeploymentStrategy    = "AllAtOnce"
  }

  lifecycle {
    ignore_changes = [
      s3_bucket,
      s3_key,
      s3_object_version,
    ]
  }
}

resource "aws_cloudwatch_log_group" "cost_explorer" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_alias" "live" {
  name             = var.environment
  function_name    = aws_lambda_function.cost_explorer.arn
  function_version = aws_lambda_function.cost_explorer.version

  lifecycle {
    ignore_changes = [function_version, routing_config]
  }
}

resource "aws_codedeploy_app" "cost_explorer" {
  name             = "${local.lambda_name}-app"
  compute_platform = local.compute_platform
}

resource "aws_iam_role" "code_deploy_role" {
  name               = "${local.lambda_name}-codedeploy-role"
  assume_role_policy = data.aws_iam_policy_document.code_deploy_assume.json
}

resource "aws_iam_role_policy" "cd_lambda" {
  name   = "${local.lambda_name}-codedeploy-lambda"
  role   = aws_iam_role.code_deploy_role.id
  policy = data.aws_iam_policy_document.codedeploy_lambda.json
}

resource "aws_codedeploy_deployment_config" "cost_explorer" {
  deployment_config_name = local.deployment_config_name
  compute_platform       = local.compute_platform

  traffic_routing_config {
    type = "AllAtOnce"
  }
}

resource "aws_codedeploy_deployment_group" "cost_explorer" {
  depends_on = [aws_codedeploy_deployment_config.cost_explorer]

  app_name              = aws_codedeploy_app.cost_explorer.name
  deployment_group_name = "${local.deployment_config_name}-dg"
  service_role_arn      = aws_iam_role.code_deploy_role.arn

  deployment_style {
    deployment_type   = "BLUE_GREEN"
    deployment_option = "WITH_TRAFFIC_CONTROL"
  }

  deployment_config_name = local.deployment_config_name

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${local.lambda_name}-daily"
  description         = "Invoke ${local.lambda_name} monthly on the 1st"
  schedule_expression = local.monthly_schedule_expression
}

resource "aws_cloudwatch_event_target" "daily" {
  rule      = aws_cloudwatch_event_rule.daily.name
  arn       = aws_lambda_alias.live.arn
  target_id = "${local.lambda_name}-daily"

  depends_on = [aws_lambda_permission.allow_eventbridge]
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "${local.lambda_name}-allow-eventbridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_explorer.function_name
  qualifier     = aws_lambda_alias.live.name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}
