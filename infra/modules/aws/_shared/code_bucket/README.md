# `_shared/code_bucket`

Shared S3 bucket for deployable artifacts.

## Owns

- frontend zip storage
- future Lambda zip storage
- future Lambda AppSpec storage

## Inputs That Change Behavior

- `frontend_artifact_dir`
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
