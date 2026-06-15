# Repo Instructions

These instructions apply to the entire repository.

## Keep `AGENTS.md` and `CLAUDE.md` identical

`REPO_INSTRUCTIONS.md` is the shared source of truth for repo guidance.

- `AGENTS.md` and `CLAUDE.md` must remain byte-for-byte identical wrapper files
  that direct the agent to read `./REPO_INSTRUCTIONS.md`.
- If you change the wrapper text in one file, make the same change in the other
  file.

## Escalation

- Request escalation for `just tg <env> <module> validate` and
  `just tg-all <env> plan|apply|destroy`.
- Prefer asking for escalation up front when the task clearly depends on AWS,
  remote state, or Route53/CloudFront state.

## Documentation Contract

- Keep docs aligned with behavior changes.
- Entry point: `README.md`.
- Workflow contracts: `.github/docs/README.md`.
- Module contracts: `infra/modules/**/README.md`.
- Runtime behavior: `frontend/` and `lambdas/README.md`.
- Before editing, read the nearest owning README for the files being changed.

## Context Loading Order

- Start with `REPO_INSTRUCTIONS.md`, then `README.md`.
- Read `.github/docs/README.md` before changing workflows or repo-local
  actions.
- Read `infra/README.md` before changing live stacks, modules, or Terragrunt
  graph behavior.

## Protected Live Stacks

- Keep `aws/oidc` in `ci`, `dev`, and `prod`.
- Keep `aws/code_bucket` in `ci` and `dev`; those buckets support frontend
  deploy artifacts now and Lambda artifacts later.

## Infra Checks

- For one concrete live stack/module, run a targeted plan such as
  `just tg dev aws/frontend plan`.
- For changes touching multiple stacks, shared modules, dependency edges, or
  workflow ordering, run an environment plan such as `just tg-all dev plan`.
- If credentials, network, permissions, or remote state block planning, say so
  and name the exact manual plan command.

## Edit Warnings

- Before editing `scripts/ci/justfile` or `scripts/deploy/justfile`, warn the
  user that the file is used by automation as well as local commands.
- Before editing `.github/workflows/shared_*.yml`, warn the user that shared CI
  workflows have broad blast radius.
