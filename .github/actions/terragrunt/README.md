# Execute Terraform & Terragrunt

This GitHub Action sets up **Terraform** and **Terragrunt** and runs a specified `terragrunt` action. When the action needs AWS, the workflow job should configure credentials first.

---

## 🚀 Features

- Installs pinned versions of Terraform and Terragrunt
- Installs Terragrunt through `jdx/mise-action@v4`
- Uses AWS credentials already configured earlier in the same job when needed
- Optionally passes Terragrunt variables via JSON tfvars
- Supports `apply`, `plan`, `apply_plan`, `destroy`, `init`, and `graph`
- Supports `plan` mode for producing local saved plan files
- Supports `init` mode for outputs-only reads
- Supports `graph` mode for raw `terragrunt run-all graph-dependencies` output capture
- Writes saved plan files into the live stack directory so workflows can upload and download them with GitHub artifacts
- Exports Terragrunt outputs as compact JSON when state exists
- Refuses to run against `infra/live/_catalog`; create a real environment under `infra/live/<name>` from the catalog before planning or applying

The Terragrunt install step is kept in this repo-local action rather than hidden behind a third-party Terragrunt wrapper action so the repo can control the exact setup-action revision and react quickly to GitHub Actions runtime deprecations or nested dependency warnings.

---

## 📥 Inputs

| Name               | Description                                                                                 | Required | Default      |
|--------------------|---------------------------------------------------------------------------------------------|----------|--------------|
| `tf_version`       | Version of Terraform to install                                                             | ❌        | `1.13.3`     |
| `tg_version`       | Version of Terragrunt to install                                                            | ❌        | `0.72.6`     |
| `aws_region`       | AWS region                                                                                  | ❌        | `eu-west-2`  |
| `override_tg_vars` | Override or additional Terragrunt variables in JSON format                                  | ❌        | `{}`         |
| `tg_directory`     | Directory containing the Terragrunt config                                                  | ✅        | —            |
| `tg_action`        | Terragrunt action: `apply`, `plan`, `apply_plan`, `destroy`, `init`, or `graph`             | ✅        | `apply`      |

`override_tg_vars` is written for `apply`, `plan`, and `destroy`, but not for `init`.

---

## 📤 Outputs

| Name                      | Description                                                                   |
|---------------------------|-------------------------------------------------------------------------------|
| `tg_outputs`              | All Terraform outputs in compact JSON. If no state exists, returns `{}`       |
| `tg_graph_output`         | Raw Terragrunt `run-all graph-dependencies` output. Set only for `graph`      |
| `plan_has_changes`        | Whether the saved plan contains changes                                       |
| `plan_artifact_directory` | Directory containing the saved plan artifact bundle                           |

---

## ⚙️ Behavior

- `apply`
  Runs `terragrunt apply -auto-approve`.
- `plan`
  Runs `terragrunt plan -detailed-exitcode -out=<live stack>/terragrunt.tfplan`. The action writes `terragrunt.plan.meta.json` for every plan run, including `has_changes` and `contains_mocked_outputs`, and writes `terragrunt.plan.txt` alongside the binary plan when the plan has changes.
- `apply_plan`
  Runs `terragrunt apply <live stack>/terragrunt.tfplan`. The calling workflow must download that stack's saved plan artifact into the live stack directory before invoking `apply_plan`. The action requires `terragrunt.plan.meta.json` to be present there. If metadata is missing, or if it says `contains_mocked_outputs: true`, the action fails before apply and tells the operator to regenerate the plan from real upstream outputs.
- `destroy`
  Runs `terragrunt destroy -auto-approve`.
- `init`
  Runs `terragrunt init -input=false -reconfigure` and then captures outputs.
- `graph`
  Runs `terragrunt run-all graph-dependencies --terragrunt-non-interactive --terragrunt-include-external-dependencies --terragrunt-log-level error` and exposes the raw output as `tg_graph_output`.

---

## 🗂 Saved Plan Layout

One run-level metadata file is stored separately by the shared infra wrapper as a GitHub Actions artifact:

- artifact name: `infra-plan-metadata`
- file: `plan-metadata.json` containing the frozen workflow inputs and derived `waves`

Each Terragrunt stack or module stores its own plan bundle as a GitHub Actions artifact named `terragrunt-plan-<environment>-<module>`:

- `terragrunt.plan.meta.json`
- `terragrunt.tfplan` only when changes exist
- `terragrunt.plan.txt` only when changes exist

---

## 🔐 AWS Credentials

Configure AWS credentials in the workflow job before calling this action. The action then reuses those ambient credentials for Terragrunt itself and for any Terragrunt-hook-driven saved-plan upload or download steps.

---

## 🛠 Example Usage

### Reuse AWS credentials already configured in the job

```yaml
jobs:
  read-outputs:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v6

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: ${{ env.AWS_OIDC_ROLE_ARN }}

      - name: Read Terragrunt outputs
        id: tg
        uses: ./.github/actions/terragrunt
        with:
          tg_directory: infra/live/dev/aws/frontend
          tg_action: init

      - name: Use outputs
        run: |
          echo '${{ steps.tg.outputs.tg_outputs }}' | jq .
```

### Minimal apply

```yaml
jobs:
  apply:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v6

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: ${{ env.AWS_OIDC_ROLE_ARN }}

      - name: Apply infrastructure
        uses: ./.github/actions/terragrunt
        with:
          tg_directory: infra/live/dev/aws/frontend
          tg_action: apply
          override_tg_vars: '{"example":"value"}'
```

### Plan

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v6

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/${{ vars.PROJECT_NAME }}-dev-github-oidc-role

      - name: Plan infrastructure
        id: tg
        uses: ./.github/actions/terragrunt
        with:
          tg_directory: infra/live/dev/aws/frontend
          tg_action: plan

      - name: Show plan result
        run: |
          echo "has_changes=${{ steps.tg.outputs.plan_has_changes }}"
          echo "artifact_dir=${{ steps.tg.outputs.plan_artifact_directory }}"
```

### Apply from downloaded GitHub artifact

```yaml
jobs:
  apply:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      actions: read

    steps:
      - uses: actions/checkout@v6

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/${{ vars.PROJECT_NAME }}-dev-github-oidc-role

      - name: Download saved plan
        uses: actions/download-artifact@v7
        with:
          name: terragrunt-plan-dev-frontend
          path: infra/live/dev/aws/frontend

      - name: Apply infrastructure from uploaded plan
        uses: ./.github/actions/terragrunt
        with:
          tg_directory: infra/live/dev/aws/frontend
          tg_action: apply_plan
```

This action expects the workflow to download the matching per-stack plan artifact into the live stack directory before using `tg_action: apply_plan`.
