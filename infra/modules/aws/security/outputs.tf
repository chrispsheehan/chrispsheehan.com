output "runtime_security_group_id" {
  value = aws_security_group.runtime.id
}

output "vpc_id" {
  value = local.vpc_id
}

output "private_subnet_ids" {
  value = data.aws_subnets.private.ids
}
