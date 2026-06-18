# `log_processor`

Concrete Lambda module for the repo's minimal deployable Lambda surface.

## Owns

- Lambda function and alias
- Lambda CloudWatch log group
- bootstrap Lambda zip object in the code bucket
- all-at-once Lambda CodeDeploy application, deployment group, and deployment config
- daily EventBridge schedule that invokes the live alias
- access to the S3 report bucket used as the temporary database
- read access to the configured CloudFront log bucket prefix
- write access to the DynamoDB processed-file ledger
- IAM roles and policies needed by the Lambda and CodeDeploy

## Key Outputs

- `lambda_function_name`
- `lambda_alias_name`
- `cloudwatch_log_group`

The current Lambda handler is `lambdas/log_processor`.
The module keeps the stable Lambda deployment surface so the code deploy
workflow can publish a new version, roll it out through CodeDeploy, and invoke
it on a daily schedule through EventBridge.

The live Terragrunt stack passes the CloudFront log bucket, report bucket,
processed-file ledger, DynamoDB region, and DynamoDB endpoint as explicit inputs
from the `s3_database` stack. The Lambda reads CloudFront log objects from the
configured log bucket under `cloudfront-logs/` by default.

`log_level` controls the Lambda's `LOG_LEVEL` environment variable and defaults
to `INFO`. Use `DEBUG` when per-date parsed record counts are needed in
CloudWatch logs.

For bootstrap-friendly plan and validate flows, keep Terragrunt dependency
mocks in the live stack rather than reading sibling state inside this module.
