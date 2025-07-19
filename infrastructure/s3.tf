# Bucket S3 para armazenamento de dados
resource "aws_s3_bucket" "bovespa_data" {
  bucket = "${var.project_name}-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "${var.project_name}-data"
    Environment = var.environment
    Purpose     = "Armazenamento de dados da Bovespa"
  }
}

# ID aleatório para sufixo do bucket
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Configuração de versionamento
resource "aws_s3_bucket_versioning" "bovespa_data_versioning" {
  bucket = aws_s3_bucket.bovespa_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Configuração de criptografia
resource "aws_s3_bucket_server_side_encryption_configuration" "bovespa_data_encryption" {
  bucket = aws_s3_bucket.bovespa_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Política de lifecycle para otimização de custos
resource "aws_s3_bucket_lifecycle_configuration" "bovespa_data_lifecycle" {
  bucket = aws_s3_bucket.bovespa_data.id

  rule {
    id     = "raw_data_lifecycle"
    status = "Enabled"

    filter {
      prefix = "raw-data/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }

  rule {
    id     = "refined_data_lifecycle"
    status = "Enabled"

    filter {
      prefix = "refined-data/"
    }

    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# Notificação S3 para acionar Lambda
resource "aws_s3_bucket_notification" "bovespa_data_notification" {
  bucket = aws_s3_bucket.bovespa_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.glue_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-data/bovespa/"
    filter_suffix       = ".parquet"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke_trigger]
}

# Política de acesso público (bloqueado por segurança)
resource "aws_s3_bucket_public_access_block" "bovespa_data_pab" {
  bucket = aws_s3_bucket.bovespa_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS Configuration (se necessário para aplicações web)
resource "aws_s3_bucket_cors_configuration" "bovespa_data_cors" {
  bucket = aws_s3_bucket.bovespa_data.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}
