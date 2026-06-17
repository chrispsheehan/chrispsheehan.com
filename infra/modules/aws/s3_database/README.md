# `s3_database`

Minimal S3-backed datastore for early-stage application state.

## Owns

- private S3 bucket
- DynamoDB processed-file ledger for CloudFront log ingestion
- public access blocking
- bucket ownership controls
- server-side encryption
- versioning

## Key Outputs

- `bucket_name`
- `bucket_arn`
- `bucket_regional_domain_name`
- `processed_log_files_table_name`
- `processed_log_files_table_arn`
- `processed_log_files_table_region`
- `processed_log_files_table_endpoint`

The module is intentionally small so application code can use S3 as a temporary
database before a relational store is introduced. The DynamoDB table is included
to give log-processing consumers an idempotent processed-object ledger without
requiring a separate live stack. Consumers should grant their own IAM access
based on these outputs.
