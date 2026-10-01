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


# Download one production-sized SQS batch and process it entirely in local temporary storage.
log-processor-integration-test sample_size='25' source_bucket='chrispsheehan.com.logs':
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"

    if ! [[ "{{sample_size}}" =~ ^[1-9][0-9]*$ ]]; then
        echo "sample_size must be a positive integer"
        exit 1
    fi

    just unit-test

    LOG_PROCESSOR_TEST_DIR="$(mktemp -d /tmp/chrispsheehan-log-processor.XXXXXX)"
    cleanup_log_processor_test() {
        if [[ "$LOG_PROCESSOR_TEST_DIR" == /tmp/chrispsheehan-log-processor.* ]]; then
            rm -rf -- "$LOG_PROCESSOR_TEST_DIR"
        fi
    }
    trap cleanup_log_processor_test EXIT

    SOURCE_DIR="$LOG_PROCESSOR_TEST_DIR/source"
    DATABASE_DIR="$LOG_PROCESSOR_TEST_DIR/database"
    SUMMARY_PATH="$LOG_PROCESSOR_TEST_DIR/summary.json"
    MANIFEST_PATH="$LOG_PROCESSOR_TEST_DIR/source-keys.txt"
    mkdir -p "$SOURCE_DIR" "$DATABASE_DIR"

    aws s3api list-objects-v2 \
        --bucket "{{source_bucket}}" \
        --prefix "cloudfront-logs/" \
        --page-size "{{sample_size}}" \
        --max-items "{{sample_size}}" \
        --query 'Contents[].Key' \
        --output text | tr '\t' '\n' > "$MANIFEST_PATH"

    DOWNLOADED=0
    while IFS= read -r KEY; do
        [[ -n "$KEY" && "$KEY" != "None" ]] || continue
        TARGET="$SOURCE_DIR/$KEY"
        mkdir -p "${TARGET%/*}"
        aws s3api get-object \
            --bucket "{{source_bucket}}" \
            --key "$KEY" \
            "$TARGET" >/dev/null
        DOWNLOADED=$((DOWNLOADED + 1))
    done < "$MANIFEST_PATH"

    if [[ "$DOWNLOADED" -ne "{{sample_size}}" ]]; then
        echo "Expected {{sample_size}} production logs, downloaded $DOWNLOADED"
        exit 1
    fi

    REPORT_BUCKET=local-report \
    S3_LOGS_BUCKET="{{source_bucket}}" \
    S3_LOGS_PREFIX=cloudfront-logs/ \
        .venv/bin/python -m lambdas.log_processor.logs_processor \
            local-log-processor \
            --local-s3-source-dir "$SOURCE_DIR" \
            --local-s3-output-dir "$DATABASE_DIR" \
            --summary-output "$SUMMARY_PATH"

    jq -e --argjson expected "$DOWNLOADED" \
        '."log-files-found" == $expected and ."log-files-processed" == $expected and ."log-files-failed" == 0' \
        "$SUMMARY_PATH" >/dev/null

    echo "Processed $DOWNLOADED production logs with temporary local state; cleanup complete on exit"


# Stop Docker Compose services and wipe local persisted service data.
docker-compose-wipe:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{PROJECT_DIR}}"
    docker compose down --volumes --remove-orphans
    rm -rf "{{PROJECT_DIR}}/docker/local-s3-database"
    mkdir -p "{{PROJECT_DIR}}/docker/local-s3-database"


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
    just git-tidy


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
