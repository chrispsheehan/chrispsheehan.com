# `_shared/oidc`

Shared GitHub Actions OIDC role module.

This repo vendors the module locally so the live `aws/oidc` stacks do not
depend on an external Terraform Registry source.

## Owns

- IAM role for GitHub Actions OIDC assumption
- attached IAM policies for state access, repo-defined AWS access, and optional
  role-management access
- lookup of the existing GitHub Actions OIDC provider in the target AWS account

## Does Not Own

- creation of the GitHub OIDC provider itself
- workflow-level `configure-aws-credentials` usage
- repo-specific decisions about how broad each environment role should be

## Requirements

- the AWS account must already contain the IAM OIDC provider for
  `https://token.actions.githubusercontent.com`
- the Terragrunt caller must provide the state bucket name
- caller policy scope is controlled by `allowed_role_actions` and
  `allowed_role_resources`

## Live Stacks

- `infra/live/ci/aws/oidc`
- `infra/live/dev/aws/oidc`
- `infra/live/prod/aws/oidc`

Apply them with:

```sh
just tg ci aws/oidc apply
just tg dev aws/oidc apply
just tg prod aws/oidc apply
```

Role names are derived from the repository name:

```text
<project_name>-<environment>-github-oidc-role
```

For this repository, `PROJECT_NAME=chrispsheehan.com`.

## Outputs Consumers Rely On

- role ARN
