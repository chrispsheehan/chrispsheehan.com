# `log_processor`

Processes CloudFront standard logs from S3 into a queryable S3 datastore.

## What It Does

- lists CloudFront `.gz` log objects under the configured S3 prefix
- claims each source object in DynamoDB before processing it
- skips source objects already marked as complete
- parses non-bot request rows from each log object
- writes newline-delimited JSON request records into date-partitioned S3 keys
- writes a small run summary to `data/log-processor/data.json`

## Invocation Modes

- Scheduled mode: invoked daily by EventBridge through the live Lambda alias
- Direct mode: invoke with `{}` to process any currently unprocessed log files

Direct mode is safe to run repeatedly. Completed source objects are skipped by
the DynamoDB ledger, and failed or interrupted objects can be claimed again on a
later run.

## Local Test Fixtures

Download a small set of CloudFront log files into `tmp/log-processor/logs`:

```sh
just lambda-log-fixtures-download
```

The fixture downloader defaults to `chrispsheehan.com.logs`, scans up to 200
objects, and downloads 10 `.gz` files. Override the limits when needed:

```sh
just lambda-log-fixtures-download 5 cloudfront-logs/ tmp/log-processor/logs
```

## Runtime Configuration

- `REPORT_BUCKET`: S3 database bucket for parsed outputs and run summary
- `S3_LOGS_BUCKET`: S3 bucket containing CloudFront `.gz` log objects
- `S3_LOGS_PREFIX`: prefix to scan for CloudFront log objects
- `PROCESSED_LOG_FILES_TABLE`: DynamoDB table used as the processed-file ledger

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
- the Lambda streams gzip objects from S3 and does not download the full log set
  to `/tmp`
- documentation files in this directory are pruned from the packaged Lambda zip
  during build
