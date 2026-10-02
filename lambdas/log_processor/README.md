# `log_processor`

Processes CloudFront standard logs from S3 into a queryable S3 datastore.

## What It Does

- lists CloudFront `.gz` log objects under the configured S3 prefix
- claims each source object with an S3 lock file before processing it
- skips source objects already marked as complete
- parses non-bot request rows from each log object
- writes newline-delimited JSON request records into date-partitioned S3 keys
- persists a private source-log cursor in the database bucket to avoid relisting
  older CloudFront log objects on every run
- consumes new-object notifications from SQS in bounded batches
- maintains one idempotent visitor-set aggregate per request date
- writes a small summary to `data/log-processor/data.json`

## Build And Deployment

`log_processor` is built into `lambdas/log_processor.zip` by the shared CI
workflow and deployed through the `infra/live/<environment>/aws/log_processor`
stack.

## Invocation Modes

- Queue mode: S3 sends new `.gz` object notifications to SQS, which invokes the
  live Lambda alias in batches
- Reconciliation mode: invoked daily by EventBridge with
  `{"reconcile": true}` to reconsider objects delivered during the last 48 hours
- Direct mode: invoke with `{}` to process any currently unprocessed log files
- Local debug mode: use the VS Code `Debug logs_report(bucket_name)` launch
  target to call `logs_report(bucket_name)` directly, bypassing
  `lambda_handler.py` and its final `data/log-processor/data.json` write
- Local refresh mode: run `just log-processor-run` to invoke
  `lambdas.log_processor.logs_processor` in Docker Compose. It reads the
  configured CloudFront logs, mirrors generated report-bucket objects and S3
  lock files under `docker/local-s3-database/`, and writes the summary
  directly to `frontend/public/data/log-processor/data.json`.
- Production-sample test mode: run `just log-processor-integration-test` to
  download 25 production log objects (one configured SQS batch) and process
  them with both source fixtures and database state isolated under `/tmp`.
  The temporary production fixtures and generated state are removed on exit.

The production-sample recipe needs read access to `chrispsheehan.com.logs`, but
does not grant the dev stack access to that bucket. It downloads only the
bounded sample before running the processor; processing itself performs no
source or database S3 requests and makes no AWS writes.

Direct mode is safe to run repeatedly. Completed source objects are skipped by
the S3 lock-file ledger, and failed or interrupted objects can be claimed again
on a later run.

SQS and S3 notifications are at-least-once. Queue handling remains idempotent:
the ledger identity uses the source bucket, key, and ETag; derived record keys
are deterministic; daily visitor updates use set union; and a source lock is
marked complete only after its aggregate update succeeds. Partial batch
responses retry only messages whose source objects failed.

The VS Code launch target always uses `local-log-processor` as the database
bucket name, prompts for `S3_LOGS_BUCKET`, and loads the remaining runtime
configuration from the repository `.env` file. S3 uses the normal boto3
credential chain and reads real CloudFront logs from the selected bucket. The
processed-file ledger and source cursor are stored in the database bucket under
`data/log-processor/`.

The pre-launch task creates `.venv` and installs
`lambdas/log_processor/requirements.txt` if needed. Keep global dummy AWS
credentials out of `.env` for this launch target, because the S3 client is
intentionally real.

## Runtime Configuration

- `REPORT_BUCKET`: S3 reports bucket for the public `data.json` summary
- `DATABASE_BUCKET`: S3 database bucket for parsed request records and lock files
- `S3_LOGS_BUCKET`: S3 bucket containing CloudFront `.gz` log objects
- `S3_LOGS_PREFIX`: prefix to scan for CloudFront log objects
- `S3_LOGS_MAX_FILES`: optional cap on claimed source log files per run
- `DATABASE_READ_WORKERS`: maximum concurrent S3 reads during visit summary
  generation; defaults to `8`
- `LOG_LEVEL`: optional Python log level; defaults to `INFO`

## Output Shape

- parsed request records:
  `data/log-processor/requests/date=<yyyy-mm-dd>/<source-hash>.jsonl`
- private processor state:
  `data/log-processor/state.json`
- incremental aggregate index:
  `data/log-processor/requests/_aggregates/state.json`
- daily unique visitor sets:
  `data/log-processor/requests/_aggregates/daily-visitors/date=<yyyy-mm-dd>.json`
- run summary:
  `data/log-processor/data.json`

Each JSONL row includes the CloudFront request date/time, viewer IP, method,
host, URI, status, referrer, user agent, edge result type, request id, and
source S3 key.

The summary counts unique viewer IPs per day from the incremental aggregate
index. A batch reads and writes only the daily visitor sets touched by its
records. When the aggregate index is absent, the processor performs a one-time
bootstrap from existing JSONL request records. The public
`data/log-processor/data.json` file contains the visit summary, a continuous
30-day `daily-visitor-counts` series with zero-filled dates, and processing
counts. It never contains viewer IPs or request records. Lambda direct
invocation responses include the summary S3 path plus current-invocation file
counters for found, claimed, processed, skipped, and failed source logs.

## Operational Notes

- the ledger key is derived from the source bucket, key, and ETag
- direct mode keeps a private source-log cursor in `state.json` and passes it
  to S3 `StartAfter`, which reduces repeated source-log listing work
- queue mode does not depend on key ordering, so delayed CloudFront logs whose
  names sort before the direct-mode cursor are still processed
- daily reconciliation scans objects delivered in the last 48 hours and lets
  the ledger discard duplicates
- the cursor only advances through a contiguous run of completed files so a
  failed or still-processing object cannot be skipped permanently
- claimed files receive a 15-minute `processing_expires_at` lease in an S3 lock
  file; concurrent workers skip active claims and only reclaim failed or expired
  processing locks
- `INFO` logs show invocation setup, listing totals, per-file claim/skip/start
  and completion progress, and the final run summary
- `DEBUG` logs include parsed record counts by source file and request date
- the Lambda streams gzip objects from S3 and does not download the full log set
  to `/tmp`
- `S3_LOGS_MAX_FILES` limits direct-mode claims; it does not truncate an SQS batch
- the first invocation after migration can take several minutes while it
  bootstraps aggregate state; later invocations are incremental
- documentation files in this directory are pruned from the packaged Lambda zip
  during build
