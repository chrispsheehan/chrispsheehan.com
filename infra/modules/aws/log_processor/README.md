# `log_processor`

Concrete Lambda module for the repo's minimal deployable Lambda surface.

## Owns

- Lambda function and alias
- Lambda CloudWatch log group
- all-at-once Lambda CodeDeploy application, deployment group, and deployment config
- daily EventBridge schedule that invokes the live alias
- access to the S3 reports bucket for the public summary
- access to the S3 database bucket used for private log-processor data
- read access to the configured CloudFront log bucket prefix
- read/write access to S3 processed-file lock objects in the report bucket
- IAM roles and policies needed by the Lambda and CodeDeploy

## Key Outputs

- `lambda_function_name`
- `lambda_alias_name`
- `cloudwatch_log_group`

The current Lambda handler is `lambdas/log_processor`.
The module keeps the stable Lambda deployment surface so the code deploy
workflow can publish a new version, roll it out through CodeDeploy, and invoke
it on a daily schedule through EventBridge.
Its bootstrap Lambda zip is the shared bootstrap object published by the
`_shared/code_bucket` module and passed in as an explicit input.

The live Terragrunt stack passes the CloudFront log bucket, reports bucket, and
database bucket as explicit inputs. The Lambda reads CloudFront log objects
from the configured log bucket under `cloudfront-logs/` by default, unless the
live stack overrides `logs_bucket_prefix`.

Production wires the CloudFront log bucket from the frontend stack outputs so it
reads the deployed site's own logs. Development can still override these values
from environment inputs when testing against another site's historical log
bucket.

`log_level` controls the Lambda's `LOG_LEVEL` environment variable and defaults
to `INFO`. Use `DEBUG` when per-date parsed record counts are needed in
CloudWatch logs.

`logs_processor_max_files` optionally sets `S3_LOGS_MAX_FILES` to cap claimed
CloudFront log files per invocation. Leave it unset for unbounded processing.

For bootstrap-friendly plan and validate flows, keep Terragrunt dependency
mocks in the live stack rather than reading sibling state inside this module.
