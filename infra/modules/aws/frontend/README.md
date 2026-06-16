# `frontend`

CloudFront frontend module for a static site.

## Owns

- private S3 origin bucket
- bucket policy granting CloudFront read access
- bucket policy granting the GitHub deploy role write access
- ACM certificate and DNS validation records
- CloudFront distribution
- Route53 `A` and `AAAA` alias records
- bootstrap `index.html` object for first-time infra deploys

## Requirements

- `hosted_zone_name` must reference an existing public Route53 hosted zone.
- `domain_prefix` is appended to `hosted_zone_name` to produce the full
  frontend domain.
- The caller must pass a `domain_aws_region` AWS provider alias in `us-east-1`
  for the CloudFront ACM certificate.

## Deployment Notes

The Terraform module uploads a bootstrap `index.html` so CloudFront can serve a
valid page before the built frontend assets are published. Later frontend
deploys replace that object with the real build output, so Terraform
intentionally ignores live content and metadata drift on that bootstrap object
after creation.

## Key Outputs

- frontend bucket name
- CloudFront distribution ID
- CloudFront domain name
- frontend URL
