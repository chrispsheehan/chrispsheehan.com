# Bootstrap Decisions

- Reference repo: `/Users/chrissheehan/git/chrispsheehan/aws-terragrunt-starter`
- Target repo: `/Users/chrissheehan/git/chrispsheehan/chrispsheehan.com`
- Mode: full scaffold into an empty target, then prune to the requested runtime
  shape
- Repo name / README title: `chrispsheehan.com`
- Current capabilities: static frontend, CloudFront, private S3 origin, Route53,
  ACM, Terragrunt infrastructure, GitHub Actions OIDC, artifact buckets, frontend
  build/deploy workflows
- Future-ready capabilities: Lambda artifact packaging/upload conventions and
  CodeDeploy AppSpec template retained for later Lambda stacks
- Removed starter capabilities: ECS cluster/service/task modules, container
  sample app, ECR, sample migrations Lambda stack
- Primary dev domain: `wip.chrispsheehan.com`
- Hosted zone: existing public `chrispsheehan.com` Route53 zone
- AWS region: `eu-west-2`
- CloudFront certificate region: `us-east-1`
- Production placeholder domain: `chrispsheehan.com`
- Frontend source replacement: copied from
  `/Users/chrissheehan/git/chrispsheehan/webstack/frontend` on 2026-06-15
  and kept as an Astro static build deployed through the existing CloudFront
  pipeline
