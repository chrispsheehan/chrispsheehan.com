locals {
  project_slug = replace(var.project_name, ".", "-")
  bucket_name  = "${var.environment}-${local.project_slug}-database"
}
