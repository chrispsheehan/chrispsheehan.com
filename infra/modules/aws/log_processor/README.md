# `log_processor`

Concrete Lambda module for the repo's minimal deployable Lambda surface.

## Owns

- Lambda function and alias
- Lambda CloudWatch log group
- all-at-once Lambda CodeDeploy application, deployment group, and deployment config
- daily EventBridge schedule that invokes the live alias
- SQS ingestion queue, dead-letter queue, and Lambda event source mapping
- S3 new-object notification filtered to the configured log prefix and `.gz` suffix
- access to the S3 reports bucket for the public summary
- access to the S3 database bucket used for private log-processor data
- read access to the configured CloudFront log bucket prefix
- read/write access to S3 processed-file lock objects and cursor state in the database bucket
- IAM roles and policies needed by the Lambda and CodeDeploy

## Key Outputs

- `lambda_function_name`
- `lambda_alias_name`
- `cloudwatch_log_group`
- `queue_url`
- `dead_letter_queue_url`

The current Lambda handler is `lambdas/log_processor`.
The module keeps the stable Lambda deployment surface so the code deploy
workflow can publish a new version and roll it out through CodeDeploy. SQS
invokes that live alias for new log objects. EventBridge performs a daily
48-hour reconciliation as a safety net for delayed or missed notifications.
Its bootstrap Lambda zip is the shared bootstrap object published by the
`_shared/code_bucket` module and passed in as an explicit input.

The live Terragrunt stack passes the CloudFront log bucket, reports bucket, and
database bucket as explicit inputs. The Lambda reads CloudFront log objects
from the configured log bucket under `cloudfront-logs/` by default, unless the
live stack overrides `logs_bucket_prefix`.

Each environment wires the CloudFront log bucket from its own frontend stack
outputs. Development consumes only `dev.chrispsheehan.com.logs`; historical
production-log testing is a local workflow and is never wired into dev AWS.

`log_level` controls the Lambda's `LOG_LEVEL` environment variable and defaults
to `INFO`. Use `DEBUG` when per-date parsed record counts are needed in
CloudWatch logs.

`logs_processor_max_files` optionally sets `S3_LOGS_MAX_FILES` to cap claimed
CloudFront log files per invocation. Leave it unset for unbounded processing.

`database_read_workers` sets `DATABASE_READ_WORKERS`, the maximum number of
concurrent S3 reads used for the one-time aggregate-state bootstrap. It defaults
to `8` and must be a positive integer.

`sqs_batch_size` defaults to `25`, and `sqs_batch_window_seconds` defaults to
`60`. The event source mapping enables partial batch responses. Failed messages
are retried five times before moving to the 14-day dead-letter queue.

`sqs_consumer_enabled` controls the event source mapping and defaults to `true`.
It provides a safe first-rollout gate while the queue accumulates notifications.

`memory_size` defaults to `512` MB to provide enough headroom for the one-time
historical aggregate bootstrap. Normal queue invocations process only their
batch and the affected daily visitor sets.

`timeout_seconds` sets the Lambda timeout. It defaults to `300` seconds and
must be an integer from `1` through AWS Lambda's 900-second maximum. Production
sets it to `900` seconds to allow the one-time summary bootstrap to finish. The
queue visibility timeout is derived from the Lambda timeout and batch window.

For the first rollout:

1. Apply the production stack once with `sqs_consumer_enabled=false`. This
   creates the queues and notification, updates IAM, and raises Lambda memory
   while leaving queued messages untouched.
2. Deploy the SQS-aware Lambda and let its direct post-deploy invocation finish
   the one-time aggregate bootstrap.
3. Apply the production stack normally to enable the event source mapping.

This prevents the previous handler from acknowledging queued notifications as
ordinary direct invocations.

For bootstrap-friendly plan and validate flows, keep Terragrunt dependency
mocks in the live stack rather than reading sibling state inside this module.
