# `cost_explorer`

Builds a small AWS Cost Explorer summary and publishes it to the shared S3
database bucket for frontend display.

## What It Does

- queries Cost Explorer for the previous month spend for this repo's tagged AWS resources
- writes the latest public summary to `data/cost-explorer/data.json`
- writes the same monthly result to a dated history key in the S3 database bucket

## Build And Deployment

`cost_explorer` is built into `lambdas/cost_explorer.zip` by the shared CI
workflow and deployed through the `infra/live/<environment>/aws/cost_explorer`
stack.

## Invocation Modes

- Scheduled mode: invoked monthly on the 1st by EventBridge through the live Lambda alias
- Direct mode: invoke with `{}` to refresh the current report immediately

## Runtime Configuration

- `REPORT_BUCKET`: S3 database bucket for the published summary
- `PROJECT_NAME`: project tag value used in the Cost Explorer filter
- `ENVIRONMENT_NAME`: environment tag value used in the Cost Explorer filter

## Output Shape

- cost summary:
  `data/cost-explorer/data.json`
- historical monthly summaries:
  `data/cost-explorer/history/month=<yyyy-mm>/data.json`

The summary currently contains `billing-month`, `last-month-total`, and
`generated-at`.
