data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
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
    actions = [
      "s3:ListBucket",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      aws_s3_bucket.frontend.arn,
      "${aws_s3_bucket.frontend.arn}/*"
    ]

    principals {
      type        = "AWS"
      identifiers = [var.deploy_role_arn]
    }
  }
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = local.caching_optimized_id
}

data "aws_cloudfront_origin_request_policy" "origin_request" {
  name = local.origin_request_policy_id
}

data "aws_cloudfront_response_headers_policy" "response_headers" {
  name = local.response_headers_policy_id
}

data "aws_caller_identity" "current" {}

data "aws_route53_zone" "frontend" {
  count        = 1
  name         = "${local.hosted_zone_name}."
  private_zone = false
}
