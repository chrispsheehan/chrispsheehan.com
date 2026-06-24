output "bucket_name" {
  value = aws_s3_bucket.frontend.id
}

output "reports_bucket_name" {
  value = aws_s3_bucket.reports.id
}

output "reports_bucket_arn" {
  value = aws_s3_bucket.reports.arn
}

output "reports_bucket_regional_domain_name" {
  value = aws_s3_bucket.reports.bucket_regional_domain_name
}

output "cloudfront_logs_bucket_name" {
  value = aws_s3_bucket.frontend_logs.id
}

output "cloudfront_logs_bucket_arn" {
  value = aws_s3_bucket.frontend_logs.arn
}

output "cloudfront_logs_prefix" {
  value = local.logs_prefix
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "domain_name" {
  value = local.domain_name
}

output "website_url" {
  value = "https://${local.domain_name}"
}
