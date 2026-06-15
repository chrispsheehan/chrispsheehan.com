# Get Changes

This GitHub Action classifies changed files into the repo's standard CI buckets. It runs through this directory's Docker image, so the local Docker path matches the workflow execution path.

---

## 🚀 Features

- Detects changed files from Git history
- Supports PR-style `base_ref...HEAD` comparisons
- Falls back to comparing against `ref` when `base_ref` is not provided
- Resolves the checkout from `GITHUB_WORKSPACE` inside GitHub Actions
- Marks the checkout as a git `safe.directory` before reading git state
- Emits one boolean output per repo CI bucket

Default path buckets:

- `actions`: `.github/actions/**`
- `terraform`: `infra/modules/**`
- `terragrunt`: `infra/**`
- `github`: `.github/**`
- `lambdas`: `lambdas/**`
- `frontend`: `frontend/**`
- `containers`: `containers/**`

---

## 📥 Inputs

| Name       | Description                                                        | Required | Default |
|------------|--------------------------------------------------------------------|----------|---------|
| `ref`      | Fallback git reference to compare from when `base_ref` is omitted  | ❌        | `main`  |
| `base_ref` | Optional explicit PR base ref or SHA for `base_ref...HEAD` compare | ❌        | `""`    |

---

## 📤 Outputs

| Name         | Description                                      |
|--------------|--------------------------------------------------|
| `actions`    | Whether repo-local GitHub action files changed   |
| `terraform`  | Whether Terraform module files changed           |
| `terragrunt` | Whether Terragrunt or infra files changed        |
| `github`     | Whether GitHub workflow or action files changed  |
| `lambdas`    | Whether Lambda source files changed              |
| `frontend`   | Whether frontend source files changed            |
| `containers` | Whether container source files changed           |

---

## 🛠 Example Usage

### Pull request diff

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
    outputs:
      lambdas: ${{ steps.filter.outputs.lambdas }}
      containers: ${{ steps.filter.outputs.containers }}

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Detect changed files
        id: filter
        uses: ./.github/actions/get-changes
        with:
          ref: ${{ github.sha }}
          base_ref: ${{ github.event.pull_request.base.sha }}
```

### Fallback ref compare

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Detect changes from main
        id: filter
        uses: ./.github/actions/get-changes
        with:
          ref: main

      - name: Use outputs
        run: |
          echo "lambdas=${{ steps.filter.outputs.lambdas }}"
          echo "containers=${{ steps.filter.outputs.containers }}"
```

---

## 💻 Local Usage

Run the action entrypoint directly:

```sh
just --justfile .github/actions/get-changes/justfile local-test --ref main
```

Run through Docker:

```sh
just --justfile .github/actions/get-changes/justfile docker-build
just --justfile .github/actions/get-changes/justfile docker-run --ref main
```

---

## 🧪 Tests

Run unit tests locally:

```sh
just --justfile .github/actions/get-changes/justfile unit-test
```

Run unit tests in Docker:

```sh
just --justfile .github/actions/get-changes/justfile docker-build
just --justfile .github/actions/get-changes/justfile docker-unit-test
```
