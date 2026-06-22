# Infrastructure

Terragrunt live stacks are under `infra/live/<environment>/aws`.

## Current Stacks

| Environment | Stacks |
| --- | --- |
| `ci` | `oidc`, `code_bucket` |
| `dev` | `oidc`, `code_bucket`, `frontend`, `security`, `s3_database`, `log_processor`, `cost_explorer` |
| `prod` | `oidc`, `frontend`, `security`, `s3_database`, `log_processor`, `cost_explorer` |

`dev` owns `dev.chrispsheehan.com`. `prod` owns
`chrispsheehan.com`.

## Frontend Module

`infra/modules/aws/frontend` owns:

- private S3 origin bucket
- CloudFront standard log bucket
- CloudFront distribution
- cached CloudFront `/data/*` behavior backed by the S3 database bucket
- ACM certificate in `us-east-1`
- Route53 `A` and `AAAA` aliases in the existing `chrispsheehan.com` hosted zone
- deploy-role write access to the origin bucket
- CloudFront read access to database `data/*` objects

## S3 Database Module

`infra/modules/aws/s3_database` owns:

- private S3 bucket for lightweight application state
- S3 lock-file ledger prefix for CloudFront log ingestion
- bucket encryption, ownership controls, public access blocking, and versioning
- bucket name, ARN, and regional domain outputs for consumers such as Lambda
  functions and CloudFront origins

## Security Module

`infra/modules/aws/security` owns:

- shared runtime security group for Lambda and future application runtimes
- runtime security group egress rules

## Artifact Buckets

`code_bucket` stores deployable `frontend/<version>/frontend.zip` artifacts now
and `lambdas/<version>/*.zip` artifacts later.

## Local Validation

```sh
terraform fmt -recursive
terragrunt hclfmt
just tg dev aws/frontend plan
just tg-all dev plan
```

Plans require AWS credentials, access to the configured remote state bucket, and
Route53/CloudFront permissions.
