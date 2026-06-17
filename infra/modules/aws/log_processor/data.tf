data "archive_file" "bootstrap_lambda" {
  type                    = "zip"
  source_content          = <<-PY
def lambda_handler(event, context):
    return {"statusCode": 200, "body": "bootstrap"}
PY
  source_content_filename = "index.py"
  output_path             = "${path.module}/bootstrap-lambda.zip"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "code_deploy_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codedeploy.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "codedeploy_lambda" {
  statement {
    sid    = "LambdaControl"
    effect = "Allow"
    actions = [
      "lambda:GetFunction",
      "lambda:PublishVersion",
      "lambda:GetAlias",
      "lambda:CreateAlias",
      "lambda:UpdateAlias",
      "lambda:ListAliases",
      "lambda:ListVersionsByFunction",
    ]
    resources = [
      aws_lambda_function.log_processor.arn,
      "${aws_lambda_function.log_processor.arn}:*",
    ]
  }

  statement {
    sid     = "ReadArtifactObject"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = [
      "arn:aws:s3:::${var.code_bucket}/*"
    ]
  }

  statement {
    sid       = "ListArtifactPrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = ["arn:aws:s3:::${var.code_bucket}"]
  }

}

data "aws_iam_policy_document" "lambda_cloudwatch_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.log_processor.arn}:*"
    ]
  }
}

data "aws_iam_policy_document" "lambda_report_bucket" {
  statement {
    sid    = "ReadLogObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${local.logs_bucket_arn}/${var.logs_bucket_prefix}*",
    ]
  }

  statement {
    sid    = "ListLogBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      local.logs_bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        var.logs_bucket_prefix,
        "${var.logs_bucket_prefix}*",
      ]
    }
  }

  statement {
    sid    = "WriteReportObject"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:PutObjectTagging",
    ]
    resources = [
      "${var.report_bucket_arn}/*",
    ]
  }

  statement {
    sid     = "ReadReportBucketLocation"
    effect  = "Allow"
    actions = ["s3:GetBucketLocation"]
    resources = [
      var.report_bucket_arn,
      local.logs_bucket_arn,
    ]
  }
}

data "aws_iam_policy_document" "lambda_processed_log_files" {
  statement {
    sid    = "WriteProcessedLogFilesLedger"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      var.processed_log_files_table_arn,
    ]
  }
}
