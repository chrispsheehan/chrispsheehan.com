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

resource "aws_iam_policy" "lambda_vpc_access" {
  name   = "${local.lambda_name}-vpc-access"
  policy = data.aws_iam_policy_document.lambda_vpc_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_vpc_access.arn
}

resource "aws_s3_object" "bootstrap_lambda_zip" {
  bucket = var.code_bucket
  key    = local.lambda_bootstrap_zip_key

  source = data.archive_file.bootstrap_lambda.output_path
  etag   = data.archive_file.bootstrap_lambda.output_md5

  content_type = "application/zip"
}

resource "aws_lambda_function" "log_processor" {
  function_name                  = local.lambda_name
  role                           = aws_iam_role.iam_for_lambda.arn
  handler                        = local.lambda_handler
  runtime                        = local.lambda_runtime
  timeout                        = 120
  reserved_concurrent_executions = 1

  s3_bucket = var.code_bucket
  s3_key    = aws_s3_object.bootstrap_lambda_zip.key

  publish = true

  vpc_config {
    subnet_ids = data.aws_subnets.private.ids
    security_group_ids = [
      var.runtime_security_group_id,
    ]
  }

  tags = {
    CodeDeployApplication = aws_codedeploy_app.log_processor.name
    CodeDeployGroup       = aws_codedeploy_deployment_group.log_processor.deployment_group_name
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

resource "aws_cloudwatch_log_group" "log_processor" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_alias" "live" {
  name             = var.environment
  function_name    = aws_lambda_function.log_processor.arn
  function_version = aws_lambda_function.log_processor.version

  lifecycle {
    ignore_changes = [function_version, routing_config]
  }
}

resource "aws_codedeploy_app" "log_processor" {
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

resource "aws_codedeploy_deployment_config" "log_processor" {
  deployment_config_name = local.deployment_config_name
  compute_platform       = local.compute_platform

  traffic_routing_config {
    type = "AllAtOnce"
  }
}

resource "aws_codedeploy_deployment_group" "log_processor" {
  depends_on = [aws_codedeploy_deployment_config.log_processor]

  app_name              = aws_codedeploy_app.log_processor.name
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
  description         = "Invoke ${local.lambda_name} daily"
  schedule_expression = local.daily_schedule_expression
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
  function_name = aws_lambda_function.log_processor.function_name
  qualifier     = aws_lambda_alias.live.name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}
