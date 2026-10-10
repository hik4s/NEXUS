# NEXUS — AWS / Terraform

## Architecture

```text
Internet
   ↓
ALB
   ↓
ECS Fargate
├── API
├── Worker
└── Scheduler
   │
   ├── RDS PostgreSQL (private)
   ├── S3 (private)
   └── CloudWatch Logs
```

The Terraform stack creates a VPC with public/private subnets, a NAT gateway, ALB, ECS cluster/services, RDS PostgreSQL, a private S3 bucket, ECR, IAM roles/policies, Secrets Manager entries and CloudWatch log groups.

## Important production note

This is intentionally a portfolio-grade single-NAT baseline. For a production deployment with stricter availability/cost requirements, use a multi-NAT or VPC endpoint strategy, multi-AZ database deployment, a release migration task, a custom HTTPS domain/certificate and external secret injection.

## Deploy

1. Install Terraform and AWS CLI.
2. Authenticate with an AWS account that has the required permissions.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Replace placeholder values.
5. Run:

```bash
terraform init
terraform fmt -check
terraform plan
terraform apply
```

## Image flow

Build/push the backend image to the ECR repository shown by `ecr_backend_repository_url`, then set `backend_image` to the immutable tag/digest you want ECS to run.

## Migrations

The baseline API task runs `alembic upgrade head` before Uvicorn. Keep `desired_backend_count = 1` until migrations are extracted into a dedicated release task.
