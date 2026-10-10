resource "aws_db_subnet_group" "nexus" {
  name       = "${local.name}-rds"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "nexus" {
  identifier = local.name

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.nexus.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  backup_retention_period = var.db_backup_retention_days
  backup_window           = "03:00-03:30"
  maintenance_window      = "sun:04:00-sun:04:30"

  deletion_protection = var.db_deletion_protection
  skip_final_snapshot = !var.db_deletion_protection
  final_snapshot_identifier = var.db_deletion_protection ? "${local.name}-final" : null

  auto_minor_version_upgrade = true
  apply_immediately           = false
}
