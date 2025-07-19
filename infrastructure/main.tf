# Configuração do provider AWS
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configurar região AWS
provider "aws" {
  region = var.aws_region
}

# Variáveis
variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "bovespa-pipeline"
}

variable "environment" {
  description = "Ambiente (dev, prod)"
  type        = string
  default     = "dev"
}

# Outputs
output "s3_bucket_name" {
  description = "Nome do bucket S3"
  value       = aws_s3_bucket.bovespa_data.id
}

output "scraper_lambda_arn" {
  description = "ARN da Lambda scraper"
  value       = aws_lambda_function.bovespa_scraper.arn
}

output "trigger_lambda_arn" {
  description = "ARN da Lambda trigger"
  value       = aws_lambda_function.glue_trigger.arn
}

output "glue_job_name" {
  description = "Nome do job Glue"
  value       = aws_glue_job.bovespa_etl.name
}
