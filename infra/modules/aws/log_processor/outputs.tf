output "lambda_function_name" {
  value = aws_lambda_function.log_processor.function_name
}

output "lambda_alias_name" {
  value = aws_lambda_alias.live.name
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.log_processor.name
}

output "queue_url" {
  value = aws_sqs_queue.log_processor.id
}

output "dead_letter_queue_url" {
  value = aws_sqs_queue.log_processor_dlq.id
}
