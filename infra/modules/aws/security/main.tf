resource "aws_security_group" "runtime" {
  name        = local.runtime_security_group_id
  description = "Security group for shared runtime resources"
  vpc_id      = local.vpc_id
}

resource "aws_vpc_security_group_egress_rule" "runtime_https_to_internet" {
  security_group_id = aws_security_group.runtime.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "Allow runtime resources to call AWS APIs over HTTPS"
}
