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


# Run Python unit tests.
unit-test:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"
    python3.12 -m venv .venv
    .venv/bin/python -m pip install --quiet --no-cache-dir \
        -r "{{PROJECT_DIR}}/{{LAMBDA_DIR}}/log_processor/requirements.txt" \
        "pytest>=8,<9"
    .venv/bin/python -m pytest


# Stop Docker Compose services and wipe local persisted service data.
docker-compose-wipe:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"
    docker compose down --volumes --remove-orphans
    rm -rf "{{PROJECT_DIR}}/docker/log-processor-s3-database"
    mkdir -p "{{PROJECT_DIR}}/docker/log-processor-s3-database"


# Run the log processor in Docker Compose and refresh the frontend summary data file.
log-processor-run:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"
    docker compose run --rm log-processor


# Return the Lambda artifact directory name.
code-bucket-get-lambda-artifact-dir:
    @echo {{LAMBDA_DIR}}


# Return the frontend artifact directory name.
code-bucket-get-frontend-artifact-dir:
    @echo {{FRONTEND_DIR}}


# Return the AppSpec artifact directory name.
code-bucket-get-appspec-artifact-dir:
    @echo {{APPSPEC_DIR}}


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


# Build the frontend, sync it to the live S3 bucket for an environment, and
# refresh the matching CloudFront distribution.
frontend-deploy-live env:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"

    if [[ "{{env}}" != "dev" && "{{env}}" != "prod" ]]; then
        echo "❌ env must be dev or prod."
        exit 1
    fi

    just --justfile "{{PROJECT_DIR}}/scripts/deploy/justfile" frontend-build

    frontend_outputs="$(
        just tg "{{env}}" aws/frontend 'output --json'
    )"

    website_bucket="$(jq -r '.bucket_name.value' <<<"$frontend_outputs")"
    distribution_id="$(jq -r '.cloudfront_distribution_id.value' <<<"$frontend_outputs")"

    if [[ -z "$website_bucket" || "$website_bucket" == "null" ]]; then
        echo "❌ Failed to read bucket_name from infra/live/{{env}}/aws/frontend output."
        exit 1
    fi

    if [[ -z "$distribution_id" || "$distribution_id" == "null" ]]; then
        echo "❌ Failed to read cloudfront_distribution_id from infra/live/{{env}}/aws/frontend output."
        exit 1
    fi

    aws s3 sync "{{PROJECT_DIR}}/{{FRONTEND_DIR}}/dist/" "s3://$website_bucket/" --delete
    DISTRIBUTION_ID="$distribution_id" \
        just --justfile "{{PROJECT_DIR}}/scripts/deploy/justfile" frontend-refresh


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
