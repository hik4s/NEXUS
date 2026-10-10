resource "aws_ecs_cluster" "nexus" {
  name = local.name
}

locals {
  runtime_environment = [
    { name = "APP_ENV", value = "production" },
    { name = "APP_NAME", value = "NEXUS API" },
    { name = "APP_VERSION", value = "0.18.0" },
    { name = "API_V1_PREFIX", value = "/api/v1" },
    { name = "REDIS_ENABLED", value = "false" },
    { name = "STORAGE_BACKEND", value = "s3" },
    { name = "S3_BUCKET", value = aws_s3_bucket.files.bucket },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "ENABLE_DOCS_IN_PRODUCTION", value = "false" },
    { name = "ENABLE_METRICS_ENDPOINT", value = "true" },
    { name = "TRUSTED_HOSTS", value = aws_lb.app.dns_name },
    { name = "CORS_ORIGINS", value = var.cors_origins },
  ]

  secret_environment = [
    { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.app_secret.arn },
    { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
  ]
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.app_cpu
  memory                   = var.app_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = var.backend_image
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = local.runtime_environment
      secrets     = local.secret_environment
      command     = ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
      healthCheck = {
        command = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readiness', timeout=3)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name}-backend"
  cluster         = aws_ecs_cluster.nexus.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_backend_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.app_cpu
  memory                   = var.app_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = var.backend_image
      essential = true
      environment = concat(
        local.runtime_environment,
        [{ name = "JOB_WORKER_POLL_SECONDS", value = "2.0" }]
      )
      secrets = local.secret_environment
      command = ["python", "-m", "app.workers.worker_loop"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name}-worker"
  cluster         = aws_ecs_cluster.nexus.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.desired_worker_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

resource "aws_ecs_task_definition" "scheduler" {
  family                   = "${local.name}-scheduler"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "scheduler"
      image     = var.backend_image
      essential = true
      environment = local.runtime_environment
      secrets = local.secret_environment
      command = ["python", "-m", "app.workers.scheduler_loop"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.scheduler.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "scheduler"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "scheduler" {
  name            = "${local.name}-scheduler"
  cluster         = aws_ecs_cluster.nexus.id
  task_definition = aws_ecs_task_definition.scheduler.arn
  desired_count   = var.desired_scheduler_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}
