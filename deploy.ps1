# Script de deploy para Windows PowerShell
# Deploy da infraestrutura AWS

Write-Host "=== Deploy do Pipeline Bovespa ===" -ForegroundColor Green

# Verificar se AWS CLI está configurado
try {
    aws sts get-caller-identity | Out-Null
    Write-Host "✓ AWS CLI configurado" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI não configurado. Execute 'aws configure' primeiro." -ForegroundColor Red
    exit 1
}

# Navegar para diretório de infraestrutura
Set-Location infrastructure

# Inicializar Terraform
Write-Host "Inicializando Terraform..." -ForegroundColor Yellow
terraform init

# Validar configuração
Write-Host "Validando configuração..." -ForegroundColor Yellow
terraform validate

# Planejar deploy
Write-Host "Planejando deploy..." -ForegroundColor Yellow
terraform plan -out=tfplan

# Confirmar deploy
$confirm = Read-Host "Deseja continuar com o deploy? (y/n)"
if ($confirm -eq 'y' -or $confirm -eq 'Y') {
    Write-Host "Executando deploy..." -ForegroundColor Green
    terraform apply tfplan
    
    Write-Host "Deploy concluído!" -ForegroundColor Green
    Write-Host "Verificando recursos criados..." -ForegroundColor Yellow
    terraform output
} else {
    Write-Host "Deploy cancelado." -ForegroundColor Yellow
    Remove-Item tfplan -ErrorAction SilentlyContinue
}

Write-Host "Script finalizado." -ForegroundColor Green
