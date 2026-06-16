# CI And Workflow Contracts

Use this when changing GitHub Actions, repo-local actions, CI helpers, deploy
workflows, or workflow-owned `just` behavior.

## Entry Points

| Workflow | Purpose |
| --- | --- |
| `pull_request.yml` | Runs change-filtered PR validation for title/version preview, wrapper sync, workflow linting, repo-local action tests, Terraform/Terragrunt formatting, Terragrunt wave shape, TFLint, frontend builds, and lambda builds. |
| `release.yml` | Tags versioned releases from `main`, publishes frontend and lambda artifacts to the CI code bucket, and creates GitHub releases. |
| `dev_infra_plan.yml` | Plans the ordered dev infra graph. |
| `dev_infra_apply_no_plan.yml` | Applies dev infrastructure using the current commit as the infra ref. |
| `dev_infra_apply_from_plan.yml` | Applies dev infra from a prior saved-plan run using `plan_artifact_run_id`. |
| `dev_code_deploy.yml` | Builds fresh frontend and lambda artifacts and deploys to dev. |
| `prod_infra_plan.yml` | Plans the ordered prod infra graph for the requested infra ref. |
| `prod_infra_apply_no_plan.yml` | Applies prod infrastructure using the pinned infra ref. |
| `prod_infra_apply_from_plan.yml` | Applies prod infra from a prior saved-plan run. |
| `prod_code_deploy.yml` | Deploys existing frontend and lambda artifacts to prod. |
| `destroy.yml` | Tears down non-shared infrastructure through the Terragrunt graph in reverse wave order. |

## Build And Deploy

`shared_build.yml` builds and publishes `frontend.zip` under
`frontend/<version>/` and `log_processor.zip` under `lambdas/<version>/` in
the selected environment code bucket.
The selected environment's `aws/code_bucket` stack must already have a real
Terraform output named `bucket`; otherwise the build fails before upload.

On the first release, `release.yml` has no prior tag to diff against, so release
notes are generated from the full history up to the new tag.

`shared_build_get.yml` resolves an existing frontend artifact from the selected
environment code bucket. Prod deploys use `environment: ci` so production
promotes frontend artifacts already present in the shared CI artifact bucket.
The Lambda artifact version is passed separately to `shared_deploy.yml`.

`shared_deploy.yml` rolls out frontend code and the `log_processor` Lambda:

- reads `bucket_name`, `cloudfront_distribution_id`, and `website_url` from
  `infra/live/<environment>/aws/frontend`
- downloads the requested `frontend.zip`
- syncs the build to the private S3 origin bucket
- creates a CloudFront invalidation
- reads `lambda_function_name` and `lambda_alias_name` from
  `infra/live/<environment>/aws/log_processor`
- publishes `lambdas/<version>/log_processor.zip`
- renders and uploads the AppSpec bundle
- starts the CodeDeploy deployment and prunes old versions
- invokes the deployed Lambda once after the rollout completes

## Infra Waves

`shared_get_modules.yml` renders the Terragrunt graph and exposes static wave
outputs consumed by shared plan/apply/destroy wrappers.

The current graph is sized for two static wave jobs:

- wave 0: roots such as `oidc`
- wave 1: dependents such as `frontend` and `code_bucket`

If the live graph grows deeper, update these workflows together:

- `shared_infra_plan.yml`
- `shared_infra_apply_no_plan.yml`
- `shared_infra_apply_from_plan.yml`
- `destroy.yml`

Then run:

```sh
just tg-graph-waves dev
```

## Saved Plans

`shared_infra_plan.yml` writes:

- run-level artifact: `infra-plan-metadata`
- per-stack artifact: `terragrunt-plan-<environment>-<module>`

`shared_infra_apply_from_plan.yml` downloads those artifacts and applies only
modules whose saved plan metadata reported changes.

Saved plans are time-limited by GitHub artifact retention.

## Repo-Local Actions

Repo-local GitHub Actions live under `.github/actions`, so workflow `uses:`
references point at local paths instead of external action tags.

- [get-changes](../actions/get-changes/README.md)
- [just](../actions/just/README.md)
- [terragrunt](../actions/terragrunt/README.md)

When a repo-local action needs AWS, configure credentials in the workflow job
before calling the action. The local action should reuse that ambient AWS
session.

## Concurrency

- Infra plans use `infra-plan-<environment>`.
- Infra applies and destroys use `infra-mutate-<environment>`.
- Code deploys use `deploy-<environment>`.
- Mutating infra workflows share `infra-mutate-<environment>`, so only one
  apply or destroy can run at a time per environment.
