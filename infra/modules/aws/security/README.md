# `security`

Shared security groups for environment-local AWS runtimes.

## Owns

- runtime security group for Lambda and future application runtimes
- HTTPS egress from runtime resources

## Key Outputs

- `runtime_security_group_id`
- `vpc_id`
- `private_subnet_ids`

The module looks up the target VPC by its `Name` tag using `vpc_name`, and
looks up private subnets in that VPC using `Name = *private*`. Keep consumers
dependent on this stack instead of creating security groups inside runtime
modules.
