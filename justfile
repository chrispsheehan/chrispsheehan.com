# List root recipes plus split CI/deploy recipe files.
_default:
    @just --list
    @printf '\nCI recipes (`just --justfile scripts/ci/justfile --list`):\n'
    @just --justfile scripts/ci/justfile --list
    @printf '\nDeploy recipes (`just --justfile scripts/deploy/justfile --list`):\n'
    @just --justfile scripts/deploy/justfile --list


PROJECT_DIR := justfile_directory()
LAMBDA_DIR := "lambdas"
FRONTEND_DIR := "frontend"
APPSPEC_DIR := "appspec"


# Start the frontend dev server.
start host='127.0.0.1' port='4321':
    #!/usr/bin/env bash
    set -euo pipefail
    npm ci --prefix "{{PROJECT_DIR}}/{{FRONTEND_DIR}}"
    npm run astro --prefix "{{PROJECT_DIR}}/{{FRONTEND_DIR}}" -- dev --host "{{host}}" --port "{{port}}"


# Return the Lambda artifact directory name.
code-bucket-get-lambda-artifact-dir:
    @echo {{LAMBDA_DIR}}


# Return the frontend artifact directory name.
code-bucket-get-frontend-artifact-dir:
    @echo {{FRONTEND_DIR}}


# Return the AppSpec artifact directory name.
code-bucket-get-appspec-artifact-dir:
    @echo {{APPSPEC_DIR}}


# Download a small CloudFront log fixture set for local Lambda testing.
lambda-log-fixtures-download limit='10' scan_limit='200':
    #!/usr/bin/env bash
    set -euo pipefail

    bucket="chrispsheehan.com.logs"
    prefix=""
    dest="{{PROJECT_DIR}}/tmp/log-processor/logs"
    limit="{{limit}}"
    scan_limit="{{scan_limit}}"

    case "$dest" in
        /*) ;;
        *) dest="{{PROJECT_DIR}}/$dest" ;;
    esac

    if ! [[ "$limit" =~ ^[0-9]+$ ]] || [[ "$limit" -lt 1 ]]; then
        echo "limit must be a positive integer" >&2
        exit 1
    fi

    if ! [[ "$scan_limit" =~ ^[0-9]+$ ]] || [[ "$scan_limit" -lt "$limit" ]]; then
        echo "scan_limit must be a positive integer greater than or equal to limit" >&2
        exit 1
    fi

    mkdir -p "$dest"
    key_file="$(mktemp)"
    trap 'rm -f "$key_file"' EXIT

    aws s3api list-objects-v2 \
      --bucket "$bucket" \
      --prefix "$prefix" \
      --max-items "$scan_limit" \
      --query 'Contents[].Key' \
      --output text \
      | tr '\t' '\n' \
      | awk -v limit="$limit" '/\.gz$/ && count < limit { print; count += 1 }' \
      > "$key_file"

    if [[ ! -s "$key_file" ]]; then
        echo "No .gz log files found in s3://$bucket/$prefix within scan_limit=$scan_limit" >&2
        exit 1
    fi

    downloaded=0
    while IFS= read -r key; do
        [[ -n "$key" ]] || continue
        local_path="$dest/$key"
        mkdir -p "$(dirname "$local_path")"
        aws s3 cp "s3://$bucket/$key" "$local_path"
        downloaded=$((downloaded + 1))
    done < "$key_file"

    echo "Downloaded $downloaded log file(s) to $dest"


# Delete local git branches whose upstream refs have gone away.
git-tidy:
    #!/usr/bin/env bash
    git fetch --prune
    for branch in $(git branch -vv | grep ': gone]' | awk '{print $1}'); do
        git branch -d $branch
    done


terraform-tidy:
    #!/usr/bin/env bash
    set -euo pipefail

    TARGET_DIR="{{justfile_directory()}}/infra/live"
    echo "Cleaning in: $TARGET_DIR"

    # Remove .terragrunt-cache directories
    find "$TARGET_DIR" -type d -name ".terragrunt-cache" -prune -exec rm -rf {} +

    # Remove .terraform.lock.hcl files
    find "$TARGET_DIR" -type f -name ".terraform.lock.hcl" -exec rm -f {} +

    echo "Done."


# Create and push a new branch from the latest `main`.
branch name:
    #!/usr/bin/env bash
    git fetch origin
    git checkout main
    git pull origin
    git checkout -b {{ name }}
    git push -u origin {{ name }}


# Run Terraform and Terragrunt formatting locally.
format:
    #!/usr/bin/env bash
    terraform fmt -recursive
    terragrunt hclfmt


# Run a Terragrunt operation for one environment/module pair.
tg env module op:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{justfile_directory()}}/infra/live/{{env}}/{{module}}
    if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
        AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
        export AWS_ACCOUNT_ID
    fi
    terragrunt {{op}}


# Run a Terragrunt operation across all live stacks.
tg-all env op:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{justfile_directory()}}/infra/live/{{env}}
    if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
        AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
        export AWS_ACCOUNT_ID
    fi
    export TF_VAR_lambda_version="this"
    terragrunt run-all {{op}}


# Print the raw Terragrunt run-all dependency graph.
tg-graph env provider='aws':
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{justfile_directory()}}/infra/live/{{env}}/{{provider}}
    if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
        AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
        export AWS_ACCOUNT_ID
    fi

    terragrunt run-all graph-dependencies \
      --terragrunt-non-interactive \
      --terragrunt-include-external-dependencies \
      --terragrunt-log-level error


# Run tg-graph once locally and feed the raw output through the CI graph and
# wave processors.
tg-graph-waves env provider='aws':
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{justfile_directory()}}

    tg_graph_json="$(
      TG_GRAPH_OUTPUT="$(just tg-graph "{{env}}" "{{provider}}")" \
        just --justfile "{{justfile_directory()}}/scripts/ci/justfile" tg-graph-output-to-json "{{env}}" "{{provider}}"
    )"

    TG_GRAPH_JSON="$tg_graph_json" \
      just --justfile "{{justfile_directory()}}/scripts/ci/justfile" tg-graph-json-to-waves
