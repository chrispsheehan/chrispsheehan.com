output "bucket_name" {
  value = aws_s3_bucket.database.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.database.arn
}
