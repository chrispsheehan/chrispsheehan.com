# Execute Just Command

This GitHub Action sets up [`just`](https://github.com/casey/just) and runs a specified **just recipe**. When the recipe needs AWS, the workflow job should configure credentials first.

---

## 🚀 Features

- Installs a specific version of [`just`](https://github.com/casey/just)
- Installs `just` through `extractions/setup-crate@v2` in the same minimal composite-action shape used by `extractions/setup-just`
- Uses AWS credentials already configured earlier in the same job when needed
- Executes any `just` command (recipe)
- Captures and returns the final line of output as an action output

---

## 📥 Inputs

| Name               | Description                                      | Required | Default      |
|--------------------|--------------------------------------------------|----------|--------------|
| `just_version`     | Version of `just` to install                     | ❌        | `1.49.0`     |
| `aws_region`       | AWS region                                       | ❌        | `eu-west-2`  |
| `just_action`      | The `just` recipe to execute                     | ✅        | —            |
| `justfile_path`    | Optional path to a specific justfile             | ❌        | `""`         |
| `mask_result`      | Use to mask value in CI                          | ❌        | `false`      |

---

## 📤 Outputs

| Name           | Description                                |
|----------------|--------------------------------------------|
| `just_outputs` | Output of the `just` command (last line)   |

---

## 🛠 Example Usage

### Reuse AWS credentials already configured in the job

```yaml
jobs:
  run-just:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: ${{ env.AWS_OIDC_ROLE_ARN }}

      - name: Run just with ambient AWS session
        uses: ./.github/actions/just
        with:
          justfile_path: scripts/ci/justfile
          just_action: some-aws-recipe
```

```just
lambda-get-version:
    #!/usr/bin/env bash
    aws lambda get-alias \
        --function-name "$FUNCTION_NAME" --name "$ALIAS_NAME" \
        --query 'FunctionVersion' --output text
```

```yaml
jobs:
  run-just:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: ${{ env.AWS_OIDC_ROLE_ARN }}

      - name: get lambda version
        id: lambda-get-version
        uses: ./.github/actions/just
        env:
          FUNCTION_NAME: dev-lambda-function
          ALIAS_NAME: dev
        with:
          just_action: lambda-get-version

      - name: read output from script
        run: |
          echo "Script output: ${{ steps.lambda-get-version.outputs.just_outputs }}"
          VERSION="${{ steps.lambda-get-version.outputs.just_outputs }}"
          echo "Parsed VERSION=$VERSION"
```

```just
get-secret:
    #!/usr/bin/env bash
    echo secret_key_or_id
```

```yaml
jobs:
  run-just:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials once
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-region: ${{ vars.AWS_REGION }}
          role-to-assume: ${{ env.AWS_OIDC_ROLE_ARN }}

      - name: get secret
        id: get-secret
        uses: ./.github/actions/just
        with:
          just_action: get-secret

      - name: read output from script
        run: |
          echo "Script output will appear *** in CI logs: ${{ steps.get-secret.outputs.just_outputs }}"
```
