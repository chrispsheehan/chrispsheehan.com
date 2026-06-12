# Repo Instructions

These instructions apply to the entire repository.

## Keep `AGENTS.md` and `CLAUDE.md` identical

`REPO_INSTRUCTIONS.md` is the shared source of truth for repo guidance.

- `AGENTS.md` and `CLAUDE.md` must remain byte-for-byte identical wrapper files that direct the agent to read `./REPO_INSTRUCTIONS.md`.
- If you change the wrapper text in one file, make the same change in the other file.
- Do not intentionally diverge the contents between those two wrapper files.

## Escalation (Commands That Often Need Real AWS/Network/Docker)

- request escalation for Terragrunt commands that need AWS credentials, remote state, or network access
- prefer asking for escalation up front when the task clearly depends on AWS, remote state, or the local Docker daemon

## Documentation Contract

- keep docs aligned with behavior changes
- README files explain the system to humans and agents; `REPO_INSTRUCTIONS.md` tells agents how to work in this repo
- keep human-facing technical contracts in the nearest owning README, not duplicated in `REPO_INSTRUCTIONS.md`
- use `REPO_INSTRUCTIONS.md` as the agent operating manual and context router
- entry point: `README.md` (human-facing high-level map, setup, and infra layout)
- module contracts: `infra/modules/**/README.md` (shared contracts live under `infra/modules/aws/_shared/**/README.md`)
- infra behavior: `infra/README.md`
- before editing, read the relevant local contract docs for the files you plan to touch and follow those contracts
- when adding or reorganizing docs, prefer short README sections that point to the owning nested README rather than expanding the root README with deep implementation detail
- when removing detail from one doc, relocate the content to the owning doc instead of dropping it; it may be shortened or clarified, but the underlying guidance must remain findable in the repo

## Context Loading Order

- load context lazily and only as needed
- start with `REPO_INSTRUCTIONS.md`, then `README.md`
- next read only the relevant contract docs for the capability subset being considered
- only after that inspect implementation files for the selected shape
- avoid loading unrelated capability areas unless the task requires them

## CI OIDC Scope

- when changing CI OIDC roles, deploy permissions, or `infra/live/ci/aws/oidc/terragrunt.hcl`, read `infra/modules/aws/_shared/oidc/README.md` and `infra/README.md` before editing
- treat the CI OIDC role as deliberately narrower than prod unless the user explicitly asks to change that contract

## Protected Live Stacks

- never remove `aws/oidc` from `infra/live/prod` or `infra/live/ci`
- treat those stacks as protected deployment scaffolding even when pruning an environment to a smaller runtime subset
- if a requested subset appears to exclude one of those protected stacks, keep the stack and call out that it is retained for workflow/bootstrap support

## Feasibility + Dependency Checks (When Editing Infra / Workflows)

- verify the runtime/deploy shape and required backing resources before changing infra or workflow ordering
- before adding environments or changing generated AWS names, verify the resulting AWS names because many names include account, region, environment, and repo name
- before adding Terragrunt dependency edges, verify the target live stack exists in that environment
- when changing reusable workflows, compare caller `with:` blocks to `workflow_call.inputs`, remove dead contract fields, and keep job `name:` values human-readable
- for cross-stack output passthroughs, preserve consumer-facing output names and update the nearest module README
- prefer Terragrunt `dependency` inputs plus `mock_outputs` over `terraform_remote_state`; if remote state is intentional, add a `# remote_state_reason: ...` comment
- when introducing or expanding bootstrap/mock-output behavior, update the nearest owning human-facing README
- for detailed checks, read `README.md` and `infra/README.md`

## Terragrunt Plan Expectation

- for a change scoped to one concrete live stack/module, run the targeted Terragrunt plan from that live stack directory, for example `infra/live/prod/aws/frontend`
- for changes touching multiple stacks, shared modules, Terragrunt dependency edges, workflow ordering, or cross-stack contracts, run plans for each affected live stack
- do not run both targeted and environment plans unless the first plan exposes a reason to broaden verification
- for noisy plans or logs, write command output under ignored `tmp/` and return only filtered summary lines such as `No changes`, `Plan:`, `Error:`, `Failed`, or relevant `WARN`
- treat saved plans as apply-intent artifacts; do not apply plans that captured bootstrap/mock values
- if credentials, network, permissions, or state access block planning, say so and name the exact manual plan command
- for saved-plan and mock-output details, read `infra/README.md`

## High-Signal Edit Warnings

- before editing repo-local command wrappers, warn the human in commentary that the file may be used by automation as well as local commands
- before editing shared workflow files, warn the human in commentary that shared CI workflows have broad blast radius
- before editing `infra/modules/aws/_shared/**`, warn the human in commentary that shared Terraform modules have broad downstream contract impact
