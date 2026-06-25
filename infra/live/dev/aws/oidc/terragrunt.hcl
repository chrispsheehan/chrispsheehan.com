include "root" {
  path = find_in_parent_folders("root.hcl")
}

terraform {
  source = "tfr:///chrispsheehan/github-oidc-role/aws?version=1.0.1"
}
