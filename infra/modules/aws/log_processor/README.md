# `log_processor`

Concrete Lambda module for the repo's minimal deployable Lambda surface.

## Owns

- Lambda function and alias
- Lambda CloudWatch log group
- bootstrap Lambda zip object in the code bucket
- all-at-once Lambda CodeDeploy application, deployment group, and deployment config
- daily EventBridge schedule that invokes the live alias
- IAM roles and policies needed by the Lambda and CodeDeploy

## Key Outputs

- `lambda_function_name`
- `lambda_alias_name`
- `cloudwatch_log_group`

The current Lambda handler is `lambdas/log_processor`.
The module keeps the stable Lambda deployment surface so the code deploy
workflow can publish a new version, roll it out through CodeDeploy, and invoke
it on a daily schedule through EventBridge.

The live Terragrunt stack passes the runtime security group id as an explicit
input. For bootstrap-friendly plan and validate flows, keep Terragrunt
dependency mocks in the live stack rather than reading sibling state inside
this module.
