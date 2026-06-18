# chrispsheehan.com

CloudFront-backed static frontend for `wip.dev.chrispsheehan.com` and
`wip.chrispsheehan.com`, scaffolded from the local `aws-terragrunt-starter`
golden path.

The current runtime is intentionally small:

- `frontend/` contains the Astro frontend source and build script.
- `infra/live/dev/aws/frontend` creates the `wip.dev.chrispsheehan.com` S3,
  CloudFront, ACM, and Route53 resources, including cached `/data/*` routing to
  the S3 database bucket.
- `infra/live/prod/aws/frontend` creates the `wip.chrispsheehan.com` S3,
  CloudFront, ACM, and Route53 resources, including cached `/data/*` routing to
  the S3 database bucket.
- `infra/live/*/aws/security` creates shared security groups for runtime
  resources.
- `infra/live/*/aws/s3_database` creates the temporary S3 datastore and
  DynamoDB ledger resources.
- `infra/live/*/aws/oidc` creates GitHub Actions deploy roles.
- `infra/live/ci/aws/code_bucket` and `infra/live/dev/aws/code_bucket` store
  deployable frontend artifacts and future Lambda artifacts.
- `lambdas/` contains Lambda source and the packaging contract, including the
  deployed `log_processor` runtime.

## Useful Commands

```sh
just --list
just start
just unit-test
just --justfile scripts/deploy/justfile frontend-build
just tg dev aws/frontend plan
just tg-all dev plan
```

## Frontend

The frontend is an Astro static site with React components.

```sh
just --justfile scripts/deploy/justfile frontend-build
```

The build output is written to `frontend/dist`.

## AWS Prerequisites

The AWS account must already contain:

- the GitHub OIDC provider for `https://token.actions.githubusercontent.com`
- the public Route53 hosted zone `chrispsheehan.com`
- an S3 backend bucket named from `infra/root.hcl`:
  `<AWS_ACCOUNT_ID>-<AWS_REGION>-chrispsheehan-com-tfstate`

## Initial OIDC Bootstrap

Create the GitHub Actions roles once from a local shell with AWS credentials
that can manage IAM:

```sh
export AWS_PROFILE=default
export AWS_REGION=eu-west-2

just tg ci aws/oidc apply
just tg dev aws/oidc apply
just tg prod aws/oidc apply
```

## GitHub Actions Variables

Set these repository variables in GitHub under
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

## Deploy Shape

Development deploys build the current commit and roll it to
`wip.dev.chrispsheehan.com`:

1. `Dev Infra Plan` / `Dev Infra Apply No Plan` creates or updates infra.
2. `Dev Code Deploy` builds `frontend.zip` and `log_processor.zip`, uploads
   them to the dev code bucket, syncs the frontend artifact to the S3 origin
   bucket, rolls the Lambda through CodeDeploy, and invokes it once.

Production deploys roll a selected frontend artifact to
`wip.chrispsheehan.com` and deploy the selected `log_processor` Lambda
artifact.

## Docs

- CI and workflow notes: [.github/docs/README.md](.github/docs/README.md)
- Infrastructure notes: [infra/README.md](infra/README.md)
- Lambda extension contract: [lambdas/README.md](lambdas/README.md)
