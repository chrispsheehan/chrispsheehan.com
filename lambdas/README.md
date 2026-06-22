# Lambdas

This directory contains Lambda source and the packaging contract shared by CI
and local deploy commands.

## Lambda Functions

- [`log_processor`](log_processor/README.md): deployed Lambda runtime.
- [`cost_explorer`](cost_explorer/README.md): deployed Lambda runtime.

## Adding Lambdas

Add each Lambda under its own directory:

```text
lambdas/
  my_function/
    lambda_handler.py
    requirements.txt
```

The deploy helper can package and upload a Lambda artifact:

```sh
LAMBDA_SOURCE_DIR=lambdas/my_function \
LAMBDA_ARTIFACT_NAME=my_function \
BUCKET_NAME=<artifact-bucket> \
VERSION=<version> \
just --justfile scripts/deploy/justfile lambda-build lambda-upload
```

Future Lambda infrastructure should add a matching live stack under
`infra/live/<environment>/aws/<lambda-name>` and a module under
`infra/modules/aws/<lambda-name>` or a shared Lambda module if multiple
functions need the same deployment shape.

`appspec-lambda.yml` is retained as a CodeDeploy template for Lambda alias
deployments.
