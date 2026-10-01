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

resource "aws_iam_policy" "lambda_sqs" {
  name   = "${local.lambda_name}-sqs"
  policy = data.aws_iam_policy_document.lambda_sqs.json
}

resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_sqs.arn
}

resource "aws_lambda_function" "log_processor" {
  function_name                  = local.lambda_name
  role                           = aws_iam_role.iam_for_lambda.arn
  handler                        = local.lambda_handler
  runtime                        = local.lambda_runtime
  timeout                        = var.timeout_seconds
  memory_size                    = var.memory_size
  reserved_concurrent_executions = 1

  s3_bucket = var.code_bucket
  s3_key    = var.bootstrap_zip_key

  publish = true

  environment {
    variables = merge(
      {
        LOG_LEVEL             = var.log_level
        REPORT_BUCKET         = var.report_bucket_name
        DATABASE_BUCKET       = var.database_bucket_name
        S3_LOGS_BUCKET        = var.logs_bucket_name
        DATABASE_READ_WORKERS = tostring(var.database_read_workers)
      },
      var.logs_bucket_prefix == "" ? {} : {
        S3_LOGS_PREFIX = var.logs_bucket_prefix
      },
      var.logs_processor_max_files == null ? {} : {
        S3_LOGS_MAX_FILES = tostring(var.logs_processor_max_files)
      },
    )
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

resource "aws_sqs_queue" "log_processor_dlq" {
  name                      = "${local.lambda_name}-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "log_processor" {
  name                       = local.lambda_name
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = min(43200, (var.timeout_seconds * 6) + var.sqs_batch_window_seconds)
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.log_processor_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_policy" "log_processor" {
  queue_url = aws_sqs_queue.log_processor.id
  policy    = data.aws_iam_policy_document.s3_to_sqs.json
}

resource "aws_s3_bucket_notification" "log_processor" {
  bucket = var.logs_bucket_name

  queue {
    queue_arn     = aws_sqs_queue.log_processor.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = var.logs_bucket_prefix
    filter_suffix = ".gz"
  }

  depends_on = [aws_sqs_queue_policy.log_processor]
}

resource "aws_lambda_event_source_mapping" "log_processor" {
  event_source_arn                   = aws_sqs_queue.log_processor.arn
  function_name                      = aws_lambda_alias.live.arn
  batch_size                         = var.sqs_batch_size
  maximum_batching_window_in_seconds = var.sqs_batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = var.sqs_consumer_enabled

  depends_on = [aws_iam_role_policy_attachment.lambda_sqs]
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
  input     = jsonencode({ reconcile = true })

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
