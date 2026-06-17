locals {
  project_slug              = replace(var.project_name, ".", "-")
  bucket_name               = "${var.environment}-${local.project_slug}-database"
  processed_log_files_table = "${var.environment}-${local.project_slug}-processed-log-files"
}
