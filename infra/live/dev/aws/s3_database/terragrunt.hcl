include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependencies {
  paths = ["../oidc"]
}

terraform {
  source = "../../../../modules//aws//s3_database"
}
