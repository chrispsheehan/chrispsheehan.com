resource "aws_s3_bucket" "code" {
  bucket        = var.code_bucket
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "code" {
  depends_on = [aws_s3_bucket.code]
  bucket     = aws_s3_bucket.code.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

locals {
  lifecycle_rules = {
    code_artifacts_lambdas = {
      days   = var.code_artifact_expiration_days
      prefix = "${var.lambda_artifact_dir}/"
    }
    code_artifacts_appspec = {
      days   = var.code_artifact_expiration_days
      prefix = "${var.appspec_artifact_dir}/"
    }
    code_artifacts_frontend = {
      days   = var.code_artifact_expiration_days
      prefix = "${var.frontend_artifact_dir}/"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "managed_artifact_retention" {
  count = length({
    for name, rule in local.lifecycle_rules : name => rule
    if rule.days > 0
  }) > 0 ? 1 : 0

  bucket = aws_s3_bucket.code.id

  dynamic "rule" {
    for_each = {
      for name, lifecycle_rule in local.lifecycle_rules : name => lifecycle_rule
      if lifecycle_rule.days > 0
    }

    content {
      id     = "delete-${rule.key}"
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      expiration {
        days = rule.value.days
      }
    }
  }
}
