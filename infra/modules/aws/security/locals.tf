locals {
  project_slug              = replace(var.project_name, ".", "-")
  runtime_security_group_id = "${var.environment}-${local.project_slug}-runtime-sg"
  vpc_id                    = data.aws_vpc.this.id
}
