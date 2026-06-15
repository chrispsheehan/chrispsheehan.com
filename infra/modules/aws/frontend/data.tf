data "aws_caller_identity" "current" {}

data "aws_route53_zone" "selected" {
  name         = var.hosted_zone_name
  private_zone = false
}

data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }

  statement {
    sid       = "AllowDeployList"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.frontend.arn]

    principals {
      type        = "AWS"
      identifiers = [var.deploy_role_arn]
    }
  }

  statement {
    sid = "AllowDeployWrite"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = [var.deploy_role_arn]
    }
  }
}
