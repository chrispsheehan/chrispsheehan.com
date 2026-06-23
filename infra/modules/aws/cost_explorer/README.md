# `cost_explorer`

Concrete Lambda module for the repo's cost summary export.

## Owns

- Lambda function and alias
- Lambda CloudWatch log group
- all-at-once Lambda CodeDeploy application, deployment group, and deployment config
- monthly EventBridge schedule on the 1st that invokes the live alias
- access to the S3 report bucket used as the temporary database
- IAM roles and policies needed by the Lambda and CodeDeploy

## Key Outputs

- `lambda_function_name`
- `lambda_alias_name`
- `cloudwatch_log_group`

The current Lambda handler is `lambdas/cost_explorer`.
The module keeps the stable Lambda deployment surface so the code deploy
workflow can publish a new version, roll it out through CodeDeploy, and invoke
it on demand after deployment.
Its bootstrap Lambda zip is the shared bootstrap object published by the
`_shared/code_bucket` module and passed in as an explicit input.

The live Terragrunt stack passes the shared S3 database bucket as an explicit
input. The Lambda writes its published summary to
`data/cost-explorer/data.json` and archives monthly results under
`data/cost-explorer/history/`.

For bootstrap-friendly plan and validate flows, keep Terragrunt dependency
mocks in the live stack rather than reading sibling state inside this module.
