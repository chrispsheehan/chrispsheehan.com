resource "aws_s3_bucket" "database" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy_db
}

resource "aws_s3_bucket_public_access_block" "database" {
  bucket = aws_s3_bucket.database.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "database" {
  bucket = aws_s3_bucket.database.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "database" {
  bucket = aws_s3_bucket.database.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "database" {
  bucket = aws_s3_bucket.database.id

  versioning_configuration {
    status = "Enabled"
  }
}
