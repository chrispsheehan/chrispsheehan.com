# `s3_database`

Minimal S3-backed datastore for early-stage application state.

## Owns

- private S3 bucket
- S3 lock-file ledger prefix for CloudFront log ingestion
- public access blocking
- bucket ownership controls
- server-side encryption
- versioning

## Key Outputs

- `bucket_name`
- `bucket_arn`
- `bucket_regional_domain_name`

The module is intentionally small so application code can use S3 as a temporary
database before a relational store is introduced. Log-processing consumers store
processed-object lock files under their own S3 prefixes in this bucket and grant
their own IAM access based on these outputs.
