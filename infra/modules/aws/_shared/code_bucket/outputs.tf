output "bucket" {
  value = aws_s3_bucket.code.bucket
}

output "bootstrap_zip_key" {
  value = aws_s3_object.shared_bootstrap_lambda_zip.key
}
