# Lambdas

No Lambda runtime is deployed yet, but `log_processor` is the first packaged
example.

This directory is kept as the future Lambda source root so Lambda code can be
added without reworking artifact conventions.

## Expected Future Shape

Add each Lambda under its own directory:

```text
lambdas/
  my_function/
    lambda_handler.py
    requirements.txt
```

The current example lives at `lambdas/log_processor` and is built into
`lambdas/log_processor.zip` by the shared CI workflow. It reads CloudFront log
objects from S3, tracks processed source files in DynamoDB, and writes parsed
JSONL records plus run summaries to the S3-backed temporary datastore
provisioned by `infra/modules/aws/s3_database`.

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
