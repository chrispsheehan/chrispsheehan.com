# `_shared/oidc`

Shared GitHub Actions OIDC role module.

This repo vendors the module locally so the live `aws/oidc` stacks do not depend on an external Terraform Registry source.

## Owns

- IAM role for GitHub Actions OIDC assumption
- attached IAM policies for state access, repo-defined AWS access, and optional role-management access
- lookup of the existing GitHub Actions OIDC provider in the target AWS account

## Does Not Own

- creation of the GitHub OIDC provider itself
- workflow-level `configure-aws-credentials` usage
- repo-specific decisions about how broad `ci`, `dev`, or `prod` access should be

## Requirements

- the AWS account must already contain the IAM OIDC provider for `https://token.actions.githubusercontent.com`
- the Terragrunt caller must provide the state bucket name
- caller policy scope is controlled by `allowed_role_actions` and `allowed_role_resources`

## Repo Contract

The live stacks are:

- `infra/live/ci/aws/oidc`
- `infra/live/prod/aws/oidc`

Apply each stack from its live directory with Terragrunt:

```sh
cd infra/live/ci/aws/oidc
terragrunt apply

cd infra/live/prod/aws/oidc
terragrunt apply
```

Role scope in this repo:

- `ci`
  intentionally narrow; currently limited to S3, IAM, and ECR actions in `infra/live/ci/environment_vars.hcl`
- `prod`
  broader deploy role for the current frontend hosting stack, including S3, IAM, CloudFront, ACM, and Route53 actions

The `ci` role is not the repo's general deploy role. If a workflow needs deploy permissions, treat that as a contract change and document the exact additional AWS actions.
Do not broaden the `ci` role to match the shared `allowed_role_actions` set unless that contract change is explicitly requested.

## Inputs That Change Behavior

- `deploy_role_name`
- `github_repo`
- `deploy_branches`
- `deploy_tags`
- `deploy_environments`
- `allow_deployments`
- `allowed_role_actions`
- `allowed_role_resources`
- `state_bucket`

In this repo, `deploy_role_name` is not set directly in each live `aws/oidc` stack. It is derived in `infra/root.hcl` and passed in through shared Terragrunt inputs:

```hcl
deploy_role_name = "${local.project_name}-${local.environment}-github-oidc-role"
```

So the current role-name pattern is:

```text
<project_name>-<environment>-github-oidc-role
```

For this repo, the role names are derived from the repository name, for example
`chrispsheehan.com-prod-github-oidc-role`.

When GitHub workflows build `AWS_OIDC_ROLE_ARN`, they use:

- `AWS_ACCOUNT_ID`
- `PROJECT_NAME`
- the workflow environment such as `ci` or `prod`

So the workflow-side ARN shape is:

```text
arn:aws:iam::<AWS_ACCOUNT_ID>:role/<PROJECT_NAME>-<environment>-github-oidc-role
```

## Outputs Consumers Rely On

- role ARN

Used by GitHub Actions via `aws-actions/configure-aws-credentials`.
