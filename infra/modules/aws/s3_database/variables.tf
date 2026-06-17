variable "project_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "environment" {
  type = string
}

variable "force_destroy_db" {
  type    = bool
  default = false
}
