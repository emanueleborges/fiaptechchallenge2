# Deploy da Infraestrutura AWS
terraform {
  backend "s3" {
    # Configurar backend remoto (opcional)
    # bucket = "meu-terraform-state-bucket"
    # key    = "bovespa-pipeline/terraform.tfstate"
    # region = "us-east-1"
  }
}

# Configurações de desenvolvimento
aws_region = "us-east-1"
project_name = "bovespa-pipeline"
environment = "dev"
