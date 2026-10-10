# NEXUS — B9 Cloud

## Official roadmap coverage

- B-051 Dockerization
- B-052 AWS compute
- B-053 AWS RDS/PostgreSQL
- B-054 AWS S3
- B-055 IAM
- B-056 CloudWatch
- B-057 Backup and recovery
- B-058 Infrastructure as Code

## Architecture choice

The reference deployment uses Amazon ECS on AWS Fargate for the API, worker and scheduler. Fargate runs containers without the project having to manage the underlying server fleet. RDS PostgreSQL is private to the VPC, and S3 is private with application-generated presigned URLs for temporary object access. CloudWatch receives container stdout/stderr through the ECS `awslogs` driver.

AWS sources:
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html

## Security model

- RDS is not public.
- S3 public access is blocked.
- ECS task IAM role is limited to the NEXUS bucket.
- Secrets are injected through AWS Secrets Manager references.
- Logs go to CloudWatch instead of being written to container disk.

## Backup baseline

RDS automated backups are enabled with a seven-day retention default and point-in-time recovery is available during that retention window. The Terraform baseline also enables deletion protection by default. AWS Backup can be added later when centralized backup policy or cross-region recovery is required.

## Validation boundary

Because the development machine currently lacks Docker, Terraform CLI and AWS CLI access, this checkpoint validates the infrastructure artifacts statically and keeps AWS runtime validation explicitly pending. No cloud deployment is claimed as tested until a real AWS environment is used.

## Local validation completed for v0.18.0

- Python compile: OK
- Backend regression suite: 66 passed
- docker-compose YAML parsing: OK
- production Dockerfile basic syntax checks: OK
- Terraform file inventory: 15 files
- Terraform delimiter/static consistency check: OK

Not validated here because the machine has no Docker/Terraform/AWS CLI or cloud credentials:
- `terraform validate`
- `terraform plan/apply`
- ECR push/pull
- ECS task startup
- ALB health check in AWS
- RDS runtime connection
- S3 real upload/download/presigned URL
- CloudWatch log delivery

Do not treat the cloud environment as deployed until those runtime checks are performed.
