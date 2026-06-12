# Infra Notes

This directory owns the current Terraform/Terragrunt infrastructure for the
frontend-only repo.

## Live Stacks

- `live/ci/aws/oidc`: GitHub Actions OIDC role for CI.
- `live/prod/aws/oidc`: GitHub Actions OIDC role for production.
- `live/prod/aws/frontend`: production static frontend hosting.

The live frontend stack depends on the prod OIDC stack because the frontend
bucket policy grants deployment access to the prod OIDC role.

## Modules

- `modules/aws/_shared/oidc`: shared GitHub Actions OIDC role module.
- `modules/aws/frontend`: static frontend hosting module.

## Terragrunt State

State is stored under:

```text
s3://<account>-<region>-<repo>-tfstate/<environment>/<provider>/<module>/terraform.tfstate
```

Terraform S3 backend lock files sit next to state objects with the `.tflock`
suffix.

## Local Terragrunt Context

`infra/root.hcl` derives account-scoped names from `AWS_ACCOUNT_ID`. Export it
before running Terragrunt directly:

```sh
export AWS_ACCOUNT_ID=<your AWS account id>
```

There is currently no repo-local `justfile` or workflow helper directory, so do
not document or assume wrapper commands unless those files are added.

## Required Backing Resources

- the Terraform state bucket named by `infra/root.hcl`
- the GitHub Actions OIDC provider in each target AWS account
- a public Route53 hosted zone for the frontend domain

See the module READMEs for stack-specific contracts.
