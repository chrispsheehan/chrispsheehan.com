output "bucket_name" {
  value = aws_s3_bucket.database.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.database.arn
}

output "processed_log_files_table_name" {
  value = aws_dynamodb_table.processed_log_files.name
}

output "processed_log_files_table_arn" {
  value = aws_dynamodb_table.processed_log_files.arn
}
