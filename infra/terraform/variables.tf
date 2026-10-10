variable "aws_region" {
  type        = string
  description = "AWS region for NEXUS."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project/application name."
  default     = "nexus"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "production"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.20.0.0/16"
}

variable "app_cpu" {
  type        = number
  default     = 512
}

variable "app_memory" {
  type        = number
  default     = 1024
}

variable "backend_image" {
  type        = string
  description = "Full ECR image URI for the backend."
}

variable "db_name" {
  type    = string
  default = "nexus"
}

variable "db_username" {
  type    = string
  default = "nexus"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "RDS master password. Prefer injecting via CI/CD secret variables."
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_engine_version" {
  type    = string
  default = "17"
}

variable "db_deletion_protection" {
  type    = bool
  default = true
}

variable "db_backup_retention_days" {
  type    = number
  default = 7
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "desired_backend_count" {
  type    = number
  default = 1
}

variable "desired_worker_count" {
  type    = number
  default = 1
}

variable "desired_scheduler_count" {
  type    = number
  default = 1
}

variable "storage_bucket_name" {
  type        = string
  description = "Globally unique private S3 bucket name for NEXUS files."
}

variable "app_secret_key" {
  type        = string
  sensitive   = true
  description = "Application/JWT secret key."
}

variable "cors_origins" {
  type        = string
  description = "Comma-separated allowed origins."
  default     = "http://localhost:5173"
}
