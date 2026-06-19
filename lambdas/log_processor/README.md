# `log_processor`

Processes CloudFront standard logs from S3 into a queryable S3 datastore.

## What It Does

- lists CloudFront `.gz` log objects under the configured S3 prefix
- claims each source object with an S3 lock file before processing it
- skips source objects already marked as complete
- parses non-bot request rows from each log object
- writes newline-delimited JSON request records into date-partitioned S3 keys
- rebuilds the public visit summary from the stored request record database
- writes a small summary to `data/log-processor/data.json`

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
  configured CloudFront logs, mirrors generated report-bucket objects and S3
  lock files under `docker/log-processor-s3-database/`, and writes the summary
  directly to `frontend/public/data/log-processor/data.json`.

Direct mode is safe to run repeatedly. Completed source objects are skipped by
the S3 lock-file ledger, and failed or interrupted objects can be claimed again
on a later run.

The VS Code launch target prompts for the report bucket name and loads the
remaining runtime configuration from the repository `.env` file. S3 uses the
normal boto3 credential chain and reads real CloudFront logs from
`S3_LOGS_BUCKET`. The processed-file ledger is stored as S3 lock files in the
report bucket under `data/log-processor/locks/`.

The pre-launch task creates `.venv` and installs
`lambdas/log_processor/requirements.txt` if needed. Keep global dummy AWS
credentials out of `.env` for this launch target, because the S3 client is
intentionally real.

## Runtime Configuration

- `REPORT_BUCKET`: S3 database bucket for parsed outputs and run summary
- `S3_LOGS_BUCKET`: S3 bucket containing CloudFront `.gz` log objects
- `S3_LOGS_PREFIX`: prefix to scan for CloudFront log objects
- `S3_LOGS_MAX_FILES`: optional cap on claimed source log files per run
- `LOG_LEVEL`: optional Python log level; defaults to `INFO`

## Output Shape

- parsed request records:
  `data/log-processor/requests/date=<yyyy-mm-dd>/<source-hash>.jsonl`
- run summary:
  `data/log-processor/data.json`

Each JSONL row includes the CloudFront request date/time, viewer IP, method,
host, URI, status, referrer, user agent, edge result type, request id, and
source S3 key.

The summary counts unique viewer IPs per day by reading all JSONL request
record files under `data/log-processor/requests/`. The public
`data/log-processor/data.json` file contains only the visit summary and
processing counts. Lambda direct invocation responses also include
`output-keys`, the stored JSONL files used for the summary, and
`run-output-keys`, the JSONL files written during the current invocation.

## Operational Notes

- the ledger key is derived from the source bucket, key, and ETag
- this avoids relying on a timestamp high-water mark, which is unsafe for
  delayed CloudFront log delivery
- claimed files receive a 15-minute `processing_expires_at` lease in an S3 lock
  file; concurrent workers skip active claims and only reclaim failed or expired
  processing locks
- `INFO` logs show invocation setup, listing totals, per-file claim/skip/start
  and completion progress, and the final run summary
- `DEBUG` logs include parsed record counts by source file and request date
- the Lambda streams gzip objects from S3 and does not download the full log set
  to `/tmp`
- `S3_LOGS_MAX_FILES` limits how many unskipped source objects are streamed in
  one run; use `S3_LOGS_PREFIX` to reduce the S3 listing scope itself
- documentation files in this directory are pruned from the packaged Lambda zip
  during build
