# `frontend`

CloudFront frontend module for a static site.

## Owns

- private S3 origin bucket
- bucket policy granting CloudFront read access
- bucket policy granting the GitHub deploy role write access
- CloudFront `/data/*` origin and cache behavior for the S3 database bucket
- bucket policy granting CloudFront read access to database `data/*` objects
- CloudFront standard log bucket and lifecycle expiry
- ACM certificate and DNS validation records
- CloudFront distribution
- Route53 `A` and `AAAA` alias records
- bootstrap `index.html` object for first-time infra deploys

## Requirements

- `hosted_zone_name` must reference an existing public Route53 hosted zone.
- `domain_prefix` is appended to `hosted_zone_name` to produce the full
  frontend domain. The private S3 origin bucket is named after this domain, and
  the CloudFront standard log bucket appends `.logs`.
- `data_bucket_name`, `data_bucket_arn`, and `data_bucket_regional_domain_name`
  must reference the S3 database bucket used for `/data/*` objects.
- The caller must pass a `domain_aws_region` AWS provider alias in `us-east-1`
  for the CloudFront ACM certificate.

## Deployment Notes

The Terraform module uploads a bootstrap `index.html` so CloudFront can serve a
valid page before the built frontend assets are published. Later frontend
deploys replace that object with the real build output, so Terraform
intentionally ignores live content and metadata drift on that bootstrap object
after creation.

The `/data/*` cache behavior serves objects from the S3 database bucket with a
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
