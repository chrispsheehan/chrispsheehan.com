# Infrastructure

Terragrunt live stacks are under `infra/live/<environment>/aws`.

## Current Stacks

| Environment | Stacks |
| --- | --- |
| `ci` | `oidc`, `code_bucket` |
| `dev` | `oidc`, `code_bucket`, `frontend`, `security`, `s3_database`, `log_processor` |
| `prod` | `oidc`, `frontend`, `security`, `s3_database`, `log_processor` |

`dev` owns `wip.dev.chrispsheehan.com`. `prod` owns
`wip.chrispsheehan.com`.

## Frontend Module

`infra/modules/aws/frontend` owns:

- private S3 origin bucket
- CloudFront distribution
- ACM certificate in `us-east-1`
- Route53 `A` and `AAAA` aliases in the existing `chrispsheehan.com` hosted zone
- deploy-role write access to the origin bucket

## S3 Database Module

`infra/modules/aws/s3_database` owns:

- private S3 bucket for lightweight application state
- DynamoDB processed-file ledger for CloudFront log ingestion
- bucket encryption, ownership controls, public access blocking, and versioning
- bucket name and ARN outputs for consumers such as Lambda functions

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
