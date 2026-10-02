include "root" {
  path = find_in_parent_folders("root.hcl")
}

# Temporary retirement stack. Keep this state path discoverable until a plan
# and apply have destroyed the former Cost Explorer resources.
terraform {
  source = "../../../../modules//aws//cost_explorer"
}
