# Arquivo ZIP para Lambda Scraper
data "archive_file" "lambda_scraper_zip" {
  type        = "zip"
  source_dir  = "../src/scraper/"
  output_path = "lambda_scraper.zip"
}

# Lambda Function para Scraper da B3
resource "aws_lambda_function" "bovespa_scraper" {
  filename         = data.archive_file.lambda_scraper_zip.output_path
  function_name    = "${var.project_name}-scraper"
  role            = aws_iam_role.lambda_scraper_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 900  # 15 minutos
  memory_size     = 1024 # 1 GB

  source_code_hash = data.archive_file.lambda_scraper_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.bovespa_data.id
      LOG_LEVEL      = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_scraper_policy,
    aws_cloudwatch_log_group.lambda_scraper_logs
  ]

  tags = {
    Name        = "${var.project_name}-scraper"
    Environment = var.environment
  }
}

# Arquivo ZIP para Lambda Trigger
data "archive_file" "lambda_trigger_zip" {
  type        = "zip"
  source_dir  = "../src/trigger/"
  output_path = "lambda_trigger.zip"
}

# Lambda Function para Trigger do Glue
resource "aws_lambda_function" "glue_trigger" {
  filename         = data.archive_file.lambda_trigger_zip.output_path
  function_name    = "${var.project_name}-glue-trigger"
  role            = aws_iam_role.lambda_trigger_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300  # 5 minutos
  memory_size     = 256  # 256 MB

  source_code_hash = data.archive_file.lambda_trigger_zip.output_base64sha256

  environment {
    variables = {
      GLUE_JOB_NAME = aws_glue_job.bovespa_etl.name
      LOG_LEVEL     = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_trigger_policy,
    aws_cloudwatch_log_group.lambda_trigger_logs
  ]

  tags = {
    Name        = "${var.project_name}-glue-trigger"
    Environment = var.environment
  }
}

# Log Groups para CloudWatch
resource "aws_cloudwatch_log_group" "lambda_scraper_logs" {
  name              = "/aws/lambda/${var.project_name}-scraper"
  retention_in_days = 14

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "lambda_trigger_logs" {
  name              = "/aws/lambda/${var.project_name}-glue-trigger"
  retention_in_days = 14

  tags = {
    Environment = var.environment
  }
}

# Permissão para S3 invocar Lambda Trigger
resource "aws_lambda_permission" "allow_s3_invoke_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.glue_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.bovespa_data.arn
}

# Permissão para EventBridge invocar Lambda Scraper
resource "aws_lambda_permission" "allow_eventbridge_invoke_scraper" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bovespa_scraper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scraper.arn
}

# EventBridge Rule para execução diária
resource "aws_cloudwatch_event_rule" "daily_scraper" {
  name                = "${var.project_name}-daily-scraper"
  description         = "Executa scraper da B3 diariamente"
  schedule_expression = "cron(0 18 * * MON-FRI *)"  # 18:00 UTC, segunda a sexta

  tags = {
    Environment = var.environment
  }
}

# Target do EventBridge
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_scraper.name
  target_id = "TargetLambdaScraper"
  arn       = aws_lambda_function.bovespa_scraper.arn

  input = jsonencode({
    "source": "eventbridge",
    "detail-type": "Scheduled Event",
    "detail": {
      "scheduled": true
    }
  })
}
