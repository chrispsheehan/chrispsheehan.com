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

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = local.name
  description                       = ""
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy.json
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

resource "aws_cloudfront_function" "spa_routing" {
  name    = "${local.name}-spa-routing"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = file("${path.module}/functions/handle-spa-routing.js")
}

resource "aws_acm_certificate" "frontend" {
  count    = 1
  provider = aws.domain_aws_region

  domain_name       = local.frontend_domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "frontend_certificate_validation" {
  for_each = {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "frontend" {
  count    = 1
  provider = aws.domain_aws_region

  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for record in aws_route53_record.frontend_certificate_validation : record.fqdn]
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = local.root_file
  comment             = local.name
  aliases             = [local.frontend_domain_name]

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    target_origin_id           = local.s3_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.origin_request.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.response_headers.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_routing.arn
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = false
    acm_certificate_arn            = aws_acm_certificate_validation.frontend[0].certificate_arn
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1.2_2021"
  }
}

resource "aws_route53_record" "frontend_alias_a" {
  count = 1

  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = local.frontend_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "frontend_alias_aaaa" {
  count = 1

  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = local.frontend_domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}
