# `cost_explorer` retirement

This temporary empty module lets the existing production Terragrunt state path
plan and apply destruction of the retired Cost Explorer resources. Development
state is already empty, so no matching development cleanup stack is needed.

After production has applied the destruction plan, remove this module and
`infra/live/prod/aws/cost_explorer`.

The generated `data/cost-explorer/` report objects are not Terraform-managed.
Delete that prefix from the production reports bucket after the frontend no
longer references it; the CloudFront `/data/*` behavior may retain cached
responses for up to 60 seconds.
