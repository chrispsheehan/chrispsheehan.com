# CI And Workflow Contracts

Use this when changing GitHub Actions, repo-local actions, CI helpers, deploy
workflows, or workflow-owned `just` behavior.

## Entry Points

| Workflow | Purpose |
| --- | --- |
| `pull_request.yml` | Runs change-filtered PR validation for title/version preview, wrapper sync, workflow linting, repo-local action tests, Terraform/Terragrunt formatting, TFLint, frontend builds, and lambda builds. |
| `release.yml` | Tags versioned releases from `main`, publishes frontend and lambda artifacts to the CI code bucket, creates GitHub releases, and dispatches the new tag to the prod deploy workflow. |
| `infra_bootstrap.yml` | Bootstraps the selected environment by applying `aws/code_bucket` first, then the full environment. |
| `infra_plan.yml` | Plans the selected environment with `terragrunt run-all` and saves reusable plan artifacts. |
| `infra_apply.yml` | Applies a prior saved-plan run for the selected environment using `plan_artifact_run_id`. |
| `dev_code_deploy.yml` | Builds fresh frontend and lambda artifacts and deploys to dev. |
| `prod_code_deploy.yml` | Validates and deploys existing frontend and lambda artifacts to prod; release dispatches it automatically and it remains manually dispatchable. |
| `destroy.yml` | Tears down infrastructure by running `terragrunt run-all destroy`, excluding `aws/oidc`. |

## Build And Deploy

`shared_build.yml` builds and publishes `frontend.zip` under
`frontend/<version>/` and `log_processor.zip` under `lambdas/<version>/` in
the selected environment code bucket.
The selected environment's `aws/code_bucket` stack is applied before build
upload so the bucket and artifact-prefix inputs are current when artifacts are
published.

On the first release, `release.yml` has no prior tag to diff against, so release
notes are generated from the full history up to the new tag.

After publishing a GitHub release, `release.yml` dispatches
`prod_code_deploy.yml` as a separate workflow run from the new tag and passes
that tag as both the frontend and Lambda artifact versions. The release run
only verifies that the production workflow was queued; deployment status and
retries remain isolated in the prod workflow run.

`shared_build_get.yml` resolves an existing frontend artifact from the selected
environment code bucket. Prod deploys use `environment: ci` so production
promotes frontend artifacts already present in the shared CI artifact bucket.
It also validates that the requested `log_processor.zip` and
`cost_explorer.zip` artifacts exist for the selected Lambda version before the
deploy wrapper continues. The prod workflow can also be dispatched manually
with a prior tag to redeploy or roll back.

`shared_code_deploy.yml` rolls out frontend code and the `log_processor`
Lambda:

- reads `bucket_name`, `cloudfront_distribution_id`, and `website_url` from
  `infra/live/<environment>/aws/frontend`
- downloads the requested `frontend.zip`
- syncs the build to the private S3 origin bucket
- runs a separate frontend cache refresh job that waits for CloudFront
  invalidation completion
- reads `lambda_function_name` and `lambda_alias_name` from
  `infra/live/<environment>/aws/log_processor`
- publishes `lambdas/<version>/log_processor.zip`
- renders and uploads the AppSpec bundle
- starts the CodeDeploy deployment and prunes old versions
- runs a separate Lambda invoke job after the Lambda deploy completes

## Shared Infra Wrappers

The infra plan/apply/destroy wrappers install Terraform and Terragrunt first,
then execute Terragrunt across the whole environment.

- They follow the same Terragrunt setup pattern as other AWS workflows.
- `infra_bootstrap.yml` first applies `aws/code_bucket`, because that stack
  publishes the shared bootstrap Lambda zip consumed by `log_processor` and
  `cost_explorer`, and then runs the full bootstrap apply.
- `infra_plan.yml` runs `terragrunt run-all plan`, then
  `terragrunt run-all show`.
- `infra_apply.yml` downloads the saved plan metadata, checks out the planned
  infra ref, and then runs `terragrunt run-all apply`.
- `destroy.yml` runs `terragrunt run-all destroy`, excluding `aws/oidc`.

Shared infra wrappers must forward permissions required by the nested reusable
call chain:

- `id-token: write` everywhere AWS OIDC is used
- `contents: read` for checkout

## Saved Plans

`infra_plan.yml` writes:

- run-level artifact: `infra-plan-metadata`
- run-level artifact: `infra-plan-files`

`infra_apply.yml` downloads those artifacts and applies only modules whose
saved plan metadata reported changes.

Saved plans are time-limited by GitHub artifact retention.

## Repo-Local Actions

Repo-local GitHub Actions live under `.github/actions`, so workflow `uses:`
references point at local paths instead of external action tags.

- [get-changes](../actions/get-changes/README.md)
- [just](../actions/just/README.md)

When a repo-local action needs AWS, configure credentials in the workflow job
before calling the action. The local action should reuse that ambient AWS
session.

## Concurrency

- Infra plans use `infra-plan-<environment>`.
- Infra applies and destroys use `infra-mutate-<environment>`.
- Code deploys use `deploy-<environment>`.
- Mutating infra workflows share `infra-mutate-<environment>`, so only one
  apply or destroy can run at a time per environment.

## Runner Image

Workflow jobs pin `runs-on` to `ubuntu-24.04` so CI and deployments do not
silently migrate when GitHub changes the operating system behind
`ubuntu-latest`. Test a newer runner image explicitly before updating the pin.
