# chrispsheehan.com

Frontend hosting infrastructure for `chrispsheehan.com`.

This repository currently contains Terraform/Terragrunt infrastructure only. It
does not contain a frontend application source tree, package manifest, or GitHub
Actions workflows yet.

## Layout

- `infra/live/ci/aws/oidc` provisions the GitHub Actions OIDC role for CI.
- `infra/live/prod/aws/oidc` provisions the GitHub Actions OIDC role for prod.
- `infra/live/prod/aws/frontend` provisions the production frontend hosting
  stack.
- `infra/modules/aws/_shared/oidc` contains the shared OIDC Terraform module.
- `infra/modules/aws/frontend` contains the static frontend hosting Terraform
  module.

See [infra/README.md](infra/README.md) for the infrastructure contract and
module-specific notes in:

- [infra/modules/aws/_shared/oidc/README.md](infra/modules/aws/_shared/oidc/README.md)
- [infra/modules/aws/frontend/README.md](infra/modules/aws/frontend/README.md)

## Current Requirements

- an AWS account with the GitHub Actions OIDC provider already present
- a Route53 public hosted zone for the frontend domain
- Terraform and Terragrunt installed locally for direct infra work
- `AWS_ACCOUNT_ID` exported before running Terragrunt directly

No Terragrunt commands were run as part of this documentation alignment.
