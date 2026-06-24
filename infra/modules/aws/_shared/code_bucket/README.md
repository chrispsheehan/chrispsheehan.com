# `_shared/code_bucket`

Shared S3 bucket for deployable artifacts.

## Owns

- frontend zip storage
- shared bootstrap zip object reused by the bootstrap Lambda consumers
- future Lambda zip storage
- future Lambda AppSpec storage

The shared bootstrap zip source lives at `bootstrap/index.py` in this module.

## Inputs That Change Behavior

- `frontend_artifact_dir`
- `lambda_bootstrap_zip_key`
- `lambda_artifact_dir`
- `appspec_artifact_dir`
- `code_artifact_expiration_days`

## Decision Rules

- `dev` keeps its own code bucket for development artifacts.
- non-`dev` environments reuse the shared `ci` code bucket for promoted
  artifacts.
- lifecycle retention is prefix-scoped for frontend, Lambda, and AppSpec
  artifacts.

## Key Outputs

- artifact bucket name
- shared bootstrap zip key
