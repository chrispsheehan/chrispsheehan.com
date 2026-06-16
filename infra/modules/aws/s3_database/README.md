# `s3_database`

Minimal S3-backed datastore for early-stage application state.

## Owns

- private S3 bucket
- public access blocking
- bucket ownership controls
- server-side encryption
- versioning

## Key Outputs

- `bucket_name`
- `bucket_arn`

The module is intentionally small so application code can use S3 as a temporary
database before a relational or key-value store is introduced. Consumers should
grant their own IAM access to the bucket based on these outputs.
