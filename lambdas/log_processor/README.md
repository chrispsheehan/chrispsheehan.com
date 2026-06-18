# `log_processor`

Processes CloudFront standard logs from S3 into a queryable S3 datastore.

## What It Does

- lists CloudFront `.gz` log objects under the configured S3 prefix
- claims each source object in DynamoDB before processing it
- skips source objects already marked as complete
- parses non-bot request rows from each log object
- writes newline-delimited JSON request records into date-partitioned S3 keys
- writes a small run summary to `data/log-processor/data.json`

## Build And Deployment

`log_processor` is built into `lambdas/log_processor.zip` by the shared CI
workflow and deployed through the `infra/live/<environment>/aws/log_processor`
stack.

## Invocation Modes

- Scheduled mode: invoked daily by EventBridge through the live Lambda alias
- Direct mode: invoke with `{}` to process any currently unprocessed log files
- Local debug mode: use the VS Code `Debug logs_report(bucket_name)` launch
  target to call `logs_report(bucket_name)` directly, bypassing
  `lambda_handler.py` and its final `data/log-processor/data.json` write
- Local refresh mode: run `just log-processor-run` to invoke
  `lambdas.log_processor.logs_processor` in Docker Compose. It reads the
  configured CloudFront logs, uses DynamoDB Local for the ledger, suppresses S3
  writes, and writes the summary directly to
  `frontend/public/data/log-processor/data.json`.

Direct mode is safe to run repeatedly. Completed source objects are skipped by
the DynamoDB ledger, and failed or interrupted objects can be claimed again on a
later run.

The VS Code launch target prompts for the report bucket name and loads the
remaining runtime configuration from the repository `.env` file. S3 uses the
normal boto3 credential chain and reads real CloudFront logs from
`S3_LOGS_BUCKET`; DynamoDB requires `DYNAMODB_ENDPOINT` and
`DYNAMODB_AWS_REGION`, so local debugging can use DynamoDB Local for the
processed-file ledger while deployed Lambda receives the AWS DynamoDB endpoint
from infrastructure.

The debug target runs the VS Code `Start DynamoDB Local` pre-launch task, which
starts `dynamodb-local` through Docker Compose and creates the processed-file
ledger table if it does not already exist.

The pre-launch task creates `.venv` and installs
`lambdas/log_processor/requirements.txt` if needed. Keep global dummy AWS
credentials out of `.env` for this launch target, because the S3 client is
intentionally real.

## Runtime Configuration

- `REPORT_BUCKET`: S3 database bucket for parsed outputs and run summary
- `S3_LOGS_BUCKET`: S3 bucket containing CloudFront `.gz` log objects
- `S3_LOGS_PREFIX`: prefix to scan for CloudFront log objects
- `S3_LOGS_MAX_FILES`: optional cap on claimed source log files per run
- `PROCESSED_LOG_FILES_TABLE`: DynamoDB table used as the processed-file ledger
- `DYNAMODB_ENDPOINT`: DynamoDB endpoint URL
- `DYNAMODB_AWS_REGION`: DynamoDB region used with `DYNAMODB_ENDPOINT`
- `LOG_LEVEL`: optional Python log level; defaults to `INFO`

## Output Shape

- parsed request records:
  `data/log-processor/requests/date=<yyyy-mm-dd>/<source-hash>.jsonl`
- run summary:
  `data/log-processor/data.json`

Each JSONL row includes the CloudFront request date/time, viewer IP, method,
host, URI, status, referrer, user agent, edge result type, request id, and
source S3 key.

## Operational Notes

- the ledger key is derived from the source bucket, key, and ETag
- this avoids relying on a timestamp high-water mark, which is unsafe for
  delayed CloudFront log delivery
- `INFO` logs show invocation setup, listing totals, per-file claim/skip/start
  and completion progress, and the final run summary
- `DEBUG` logs include parsed record counts by source file and request date
- the Lambda streams gzip objects from S3 and does not download the full log set
  to `/tmp`
- `S3_LOGS_MAX_FILES` limits how many unskipped source objects are streamed in
  one run; use `S3_LOGS_PREFIX` to reduce the S3 listing scope itself
- documentation files in this directory are pruned from the packaged Lambda zip
  during build
