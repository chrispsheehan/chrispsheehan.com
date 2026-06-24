# `frontend`

CloudFront frontend module for a static site.

## Owns

- private S3 origin bucket
- private S3 reports bucket for public generated `/data/*` artifacts
- bucket policy granting CloudFront read access
- bucket policy granting the GitHub deploy role write access
- CloudFront `/data/*` origin and cache behavior for the reports bucket
- bucket policy granting CloudFront read access to reports `data/*` objects
- CloudFront standard log bucket and lifecycle expiry
- ACM certificate and DNS validation records
- CloudFront distribution
- Route53 `A` and `AAAA` alias records
- bootstrap `index.html` object for first-time infra deploys

## Requirements

- `hosted_zone_name` must reference an existing public Route53 hosted zone.
- `domain_prefix` is prepended to `hosted_zone_name` to produce the full
  frontend domain. Pass an empty string to use the hosted zone apex. The
  private S3 origin bucket is named after this domain, and the CloudFront
  standard log bucket appends `.logs`.
- `alternate_domain_prefixes` builds extra DNS names from the frontend domain
  and adds them to the same ACM certificate, CloudFront aliases, and Route53
  alias records. The default adds `www.<frontend-domain>`.
- The caller must pass a `domain_aws_region` AWS provider alias in `us-east-1`
  for the CloudFront ACM certificate.

## Deployment Notes

The Terraform module uploads a bootstrap `index.html` so CloudFront can serve a
valid page before the built frontend assets are published. Later frontend
deploys replace that object with the real build output, so Terraform
intentionally ignores live content and metadata drift on that bootstrap object
after creation.

The `/data/*` cache behavior serves objects from the module-managed reports bucket with a
60 second TTL. This exposes generated files such as
`/data/log-processor/data.json` through the same CloudFront distribution as the
static frontend.

CloudFront standard logs are written to the module-managed logs bucket under
`cloudfront-logs/`. The log processor source bucket is configured separately, so
dev and prod can still read historical test logs from another site such as
`chrispsheehan.com.logs`.

## Key Outputs

- frontend bucket name
- CloudFront logs bucket name, ARN, and prefix
- CloudFront distribution ID
- CloudFront domain name
- frontend URL
