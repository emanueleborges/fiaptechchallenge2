# Bucket S3 para scripts do Glue
resource "aws_s3_bucket" "glue_scripts" {
  bucket = "${var.project_name}-glue-scripts-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "${var.project_name}-glue-scripts"
    Environment = var.environment
    Purpose     = "Scripts do AWS Glue"
  }
}

# Upload do script do Glue para S3
resource "aws_s3_object" "glue_job_script" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "scripts/bovespa_etl_job.py"
  source = "../src/glue/job_script.py"
  etag   = filemd5("../src/glue/job_script.py")

  tags = {
    Environment = var.environment
  }
}

# Glue Database
resource "aws_glue_catalog_database" "bovespa_database" {
  name        = "bovespa_database"
  description = "Database para dados da Bovespa"

  catalog_id = data.aws_caller_identity.current.account_id
}

# Glue Job para ETL
resource "aws_glue_job" "bovespa_etl" {
  name         = "${var.project_name}-etl-job"
  role_arn     = aws_iam_role.glue_job_role.arn
  glue_version = "4.0"

  command {
    script_location = "s3://${aws_s3_bucket.glue_scripts.id}/scripts/bovespa_etl_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-bookmark-option"                     = "job-bookmark-enable"
    "--enable-metrics"                          = ""
    "--enable-continuous-cloudwatch-log"       = "true"
    "--enable-glue-datacatalog"                = ""
    "--enable-spark-ui"                         = "true"
    "--spark-event-logs-path"                   = "s3://${aws_s3_bucket.bovespa_data.id}/sparkHistoryLogs/"
    "--additional-python-modules"               = "boto3,pandas"
    "--conf"                                    = "spark.sql.adaptive.enabled=true"
    "--conf"                                    = "spark.sql.adaptive.coalescePartitions.enabled=true"
  }

  execution_property {
    max_concurrent_runs = 3
  }

  max_retries = 2
  timeout     = 60  # 60 minutos
  
  # Número de workers (DPUs)
  number_of_workers = 2
  worker_type       = "G.1X"

  tags = {
    Name        = "${var.project_name}-etl-job"
    Environment = var.environment
  }

  depends_on = [
    aws_s3_object.glue_job_script,
    aws_glue_catalog_database.bovespa_database
  ]
}

# Glue Crawler para catalogar dados refinados
resource "aws_glue_crawler" "bovespa_refined_crawler" {
  database_name = aws_glue_catalog_database.bovespa_database.name
  name          = "${var.project_name}-refined-crawler"
  role          = aws_iam_role.glue_crawler_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.bovespa_data.id}/refined-data/bovespa/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
    }
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })

  schedule = "cron(0 6 * * ? *)"  # 6:00 AM UTC diariamente

  tags = {
    Name        = "${var.project_name}-refined-crawler"
    Environment = var.environment
  }
}

# Role para Glue Crawler
resource "aws_iam_role" "glue_crawler_role" {
  name = "${var.project_name}-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# Política padrão do Glue para Crawler
resource "aws_iam_role_policy_attachment" "glue_crawler_service_role" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Política customizada para Crawler
resource "aws_iam_role_policy" "glue_crawler_policy" {
  name = "${var.project_name}-glue-crawler-policy"
  role = aws_iam_role.glue_crawler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bovespa_data.arn,
          "${aws_s3_bucket.bovespa_data.arn}/*"
        ]
      }
    ]
  })
}

# Glue Trigger para iniciar crawler após job ETL
resource "aws_glue_trigger" "start_crawler_after_etl" {
  name = "${var.project_name}-start-crawler-trigger"
  type = "CONDITIONAL"

  actions {
    crawler_name = aws_glue_crawler.bovespa_refined_crawler.name
  }

  predicate {
    conditions {
      job_name = aws_glue_job.bovespa_etl.name
      state    = "SUCCEEDED"
    }
  }

  tags = {
    Name        = "${var.project_name}-crawler-trigger"
    Environment = var.environment
  }
}

# Data source para account ID
data "aws_caller_identity" "current" {}

# CloudWatch Log Group para Glue Job
resource "aws_cloudwatch_log_group" "glue_job_logs" {
  name              = "/aws-glue/jobs/${aws_glue_job.bovespa_etl.name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}
