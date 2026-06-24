# chrispsheehan.com

[![Release](https://img.shields.io/github/v/release/chrispsheehan/chrispsheehan.com?display_name=tag&label=Release)](https://github.com/chrispsheehan/chrispsheehan.com/releases)
[![Infra Plan](https://img.shields.io/github/actions/workflow/status/chrispsheehan/chrispsheehan.com/prod_infra_plan.yml?label=Infra%20Plan)](https://github.com/chrispsheehan/chrispsheehan.com/actions/workflows/prod_infra_plan.yml)
[![Infra Apply](https://img.shields.io/github/actions/workflow/status/chrispsheehan/chrispsheehan.com/prod_infra_apply_from_plan.yml?label=Infra%20Apply)](https://github.com/chrispsheehan/chrispsheehan.com/actions/workflows/prod_infra_apply_from_plan.yml)
[![Code Deploy](https://img.shields.io/github/actions/workflow/status/chrispsheehan/chrispsheehan.com/prod_code_deploy.yml?label=Code%20Deploy)](https://github.com/chrispsheehan/chrispsheehan.com/actions/workflows/prod_code_deploy.yml)

CloudFront-backed static frontend for [`chrispsheehan.com`](https://chrispsheehan.com), scaffolded from the [`aws-terragrunt-starter`](https://github.com/chrispsheehan/aws-terragrunt-starter)
golden path.

This repo contains the site frontend, its small supporting Lambda set, and the
AWS infrastructure used to build and deploy both.

## Start Here

If you just need to get oriented:

1. Read the repo layout below.
2. Run `just --list` to see the available local workflows.
3. Use `just start` for local frontend work.
4. Use `just tg dev aws/frontend plan` when you need to inspect the dev stack.

## Repo Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Astro static site with React components. Build output goes to `frontend/dist`. |
| `lambdas/` | Lambda source, packaging contract, and runtime notes for `log_processor` and `cost_explorer`. |
| `infra/` | Terragrunt live stacks and shared Terraform modules for frontend, data, security, OIDC, and artifact storage. |

## Common Commands

The commands most people reach for first are:

```sh
just --list
just start
just unit-test
just log-processor-run
just frontend-deploy-live dev
just tg dev aws/frontend plan
just tg-all dev plan
AWS_REGION=eu-west-2 LAMBDA_NAME=prod-chrispsheehan-com-log-processor just --justfile scripts/deploy/justfile lambda-invoke
```

## Setup

The AWS account must already contain:

- the GitHub OIDC provider for `https://token.actions.githubusercontent.com`
- the public Route53 hosted zone `chrispsheehan.com`
- an S3 backend bucket named from `infra/root.hcl`:
  `<AWS_ACCOUNT_ID>-<AWS_REGION>-chrispsheehan-com-tfstate`

Bootstrap GitHub Actions roles once from a local shell with AWS credentials
that can manage IAM:

```sh
export AWS_PROFILE=default
export AWS_REGION=eu-west-2

just tg ci aws/oidc apply
just tg dev aws/oidc apply
just tg prod aws/oidc apply
```

Set these GitHub repository variables under
`Settings -> Secrets and variables -> Actions -> Variables`:

```text
AWS_ACCOUNT_ID=<your AWS account id>
AWS_REGION=eu-west-2
PROJECT_NAME=chrispsheehan.com
```

Workflows assume roles named:

```text
<PROJECT_NAME>-<ENVIRONMENT>-github-oidc-role
```

## Deploys

Development deploys target `dev.chrispsheehan.com` and build from the current
commit.

- `Dev Infra Plan` and `Dev Infra Apply No Plan` create or update the AWS
  infrastructure.
- `Dev Code Deploy` builds `frontend.zip`, `log_processor.zip`, and
  `cost_explorer.zip`, uploads them to the dev code bucket, syncs the frontend
  artifact to the S3 origin bucket, refreshes CloudFront in a separate CI job,
  rolls both Lambdas through CodeDeploy, and invokes each Lambda once in a
  separate CI job.

Production deploys target `chrispsheehan.com`.

- Production rolls a selected frontend artifact and the selected
  `log_processor` and `cost_explorer` Lambda artifacts.

## Further Reading

- CI and workflow notes: [.github/docs/README.md](.github/docs/README.md)
- Infrastructure notes: [infra/README.md](infra/README.md)
- Lambda extension contract: [lambdas/README.md](lambdas/README.md)
