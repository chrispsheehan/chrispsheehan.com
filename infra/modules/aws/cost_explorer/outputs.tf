output "lambda_function_name" {
  value = aws_lambda_function.cost_explorer.function_name
}

output "lambda_alias_name" {
  value = aws_lambda_alias.live.name
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.cost_explorer.name
}
