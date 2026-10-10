output "alb_dns_name" {
  value       = aws_lb.app.dns_name
  description = "Public NEXUS API endpoint."
}

output "rds_endpoint" {
  value       = aws_db_instance.nexus.address
  description = "Private RDS endpoint."
}

output "s3_bucket" {
  value       = aws_s3_bucket.files.bucket
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.nexus.name
}
