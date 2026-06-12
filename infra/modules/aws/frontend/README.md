# `frontend`

Static frontend hosting module.

## Owns

- website bucket and distribution resources
- bootstrap `index.html` object for first-time infra deploys
- ACM certificate and Route53 alias records for the derived CloudFront custom domain
- deployment destination for built frontend assets
- SPA routing through a CloudFront Function

## Dependencies

- pre-existing Route53 hosted zone for the chosen frontend domain
- caller-provided deploy role ARN for S3 object deployment access

## Routing behavior

All paths are served from the frontend bucket with SPA routing.

## Custom domain

The module expects `domain_name` for hosted-zone lookup.
By default it derives the deployed frontend URL as `<project_name>.<environment>.<domain_name>`, but callers can set `frontend_domain_name` to publish an exact host such as `chrispsheehan.com`.
It requests an ACM certificate in `us-east-1`, validates it with Route53 DNS records, and creates `A` and `AAAA` alias records in the matching hosted zone.
If `frontend_hosted_zone_name` is omitted, the module uses `domain_name` itself as the hosted zone, which fits names like `example.com`.

If the hosted zone does not already exist, certificate validation and alias-record creation will fail.

## Key outputs

- website bucket name
- CloudFront distribution id
- CloudFront distribution domain name
- HTTPS frontend URL

These outputs are intended for a future frontend build and deploy workflow path.

The Terraform module uploads a bootstrap `index.html` so the distribution serves a valid page before the built frontend assets are published. Later frontend deploys replace that object with the real app bundle output, so Terraform intentionally ignores live content and metadata drift on that bootstrap object after creation.
