# Infrastructure

Terragrunt live stacks are under `infra/live/<environment>/aws`.

## Current Stacks

| Environment | Stacks |
| --- | --- |
| `ci` | `oidc`, `code_bucket` |
| `dev` | `oidc`, `code_bucket`, `frontend` |
| `prod` | `oidc`, `frontend` |

`dev` owns `wip.chrispsheehan.com`. `prod` is scaffolded with
`chrispsheehan.com` in `infra/live/prod/environment_vars.hcl`; change that
before applying prod if needed.

## Frontend Module

`infra/modules/aws/frontend` owns:

- private S3 origin bucket
- CloudFront distribution
- ACM certificate in `us-east-1`
- Route53 `A` and `AAAA` aliases in the existing `chrispsheehan.com` hosted zone
- deploy-role write access to the origin bucket

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
