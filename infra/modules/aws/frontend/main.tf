resource "aws_s3_bucket" "frontend" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket" "frontend_logs" {
  bucket        = local.logs_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "frontend_logs" {
  bucket = aws_s3_bucket.frontend_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "frontend_logs" {
  bucket = aws_s3_bucket.frontend_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "frontend_logs" {
  bucket = aws_s3_bucket.frontend_logs.id

  rule {
    id     = "expire-cloudfront-logs"
    status = "Enabled"

    filter {
      prefix = local.logs_prefix
    }

    expiration {
      days = var.log_retention_days
    }
  }
}

resource "aws_acm_certificate" "frontend" {
  provider                  = aws.domain_aws_region
  domain_name               = local.domain_name
  subject_alternative_names = local.domain_records
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  for_each = toset(local.domain_records)

  allow_overwrite = true
  name = one([
    for option in aws_acm_certificate.frontend.domain_validation_options :
    option.resource_record_name
    if option.domain_name == each.value
  ])
  records = [one([
    for option in aws_acm_certificate.frontend.domain_validation_options :
    option.resource_record_value
    if option.domain_name == each.value
  ])]
  ttl = 60
  type = one([
    for option in aws_acm_certificate.frontend.domain_validation_options :
    option.resource_record_type
    if option.domain_name == each.value
  ])
  zone_id = data.aws_route53_zone.selected.zone_id
}

resource "aws_acm_certificate_validation" "frontend" {
  provider                = aws.domain_aws_region
  certificate_arn         = aws_acm_certificate.frontend.arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${local.name}-frontend"
  description                       = "Allow CloudFront to read the ${local.domain_name} frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  depends_on = [aws_s3_bucket_ownership_controls.frontend_logs]

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.environment} ${var.project_name} frontend"
  default_root_object = local.root_file
  aliases             = local.domain_records
  price_class         = "PriceClass_100"

  logging_config {
    bucket          = aws_s3_bucket.frontend_logs.bucket_regional_domain_name
    include_cookies = false
    prefix          = local.logs_prefix
  }

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
    origin_id                = local.cloudfront_origin_id
  }

  origin {
    domain_name              = var.data_bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
    origin_id                = local.data_origin_id
  }

  ordered_cache_behavior {
    path_pattern           = "/data/*"
    target_origin_id       = local.data_origin_id
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 60
    max_ttl     = 60
    compress    = true
  }

  default_cache_behavior {
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods           = ["GET", "HEAD"]
    target_origin_id         = local.cloudfront_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    cache_policy_id          = local.managed_cache_policy
    origin_request_policy_id = local.managed_origin_policy
    compress                 = true
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/${local.root_file}"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/${local.root_file}"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.frontend.certificate_arn
    minimum_protocol_version = "TLSv1.2_2021"
    ssl_support_method       = "sni-only"
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy.json
}

resource "aws_s3_bucket_policy" "data" {
  bucket = var.data_bucket_name
  policy = data.aws_iam_policy_document.data_bucket_policy.json
}

resource "aws_route53_record" "frontend_ipv4" {
  for_each = {
    for index, record in local.domain_records : index => record
  }

  name    = each.value
  type    = "A"
  zone_id = data.aws_route53_zone.selected.zone_id

  alias {
    evaluate_target_health = false
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
  }
}

resource "aws_route53_record" "frontend_ipv6" {
  for_each = {
    for index, record in local.domain_records : index => record
  }

  name    = each.value
  type    = "AAAA"
  zone_id = data.aws_route53_zone.selected.zone_id

  alias {
    evaluate_target_health = false
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
  }
}

resource "aws_s3_object" "bootstrap_index" {
  bucket       = aws_s3_bucket.frontend.id
  key          = local.root_file
  source       = "${path.module}/bootstrap/index.html"
  etag         = filemd5("${path.module}/bootstrap/index.html")
  content_type = "text/html; charset=utf-8"

  lifecycle {
    ignore_changes = [
      content_type,
      etag,
      source,
      tags_all,
    ]
  }
}
