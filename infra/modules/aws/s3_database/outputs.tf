output "bucket_name" {
  value = aws_s3_bucket.database.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.database.arn
}

output "bucket_regional_domain_name" {
  value = aws_s3_bucket.database.bucket_regional_domain_name
}

output "processed_log_files_table_name" {
  value = aws_dynamodb_table.processed_log_files.name
}

output "processed_log_files_table_arn" {
  value = aws_dynamodb_table.processed_log_files.arn
}

output "processed_log_files_table_region" {
  value = var.aws_region
}

output "processed_log_files_table_endpoint" {
  value = "https://dynamodb.${var.aws_region}.${data.aws_partition.current.dns_suffix}"
}
