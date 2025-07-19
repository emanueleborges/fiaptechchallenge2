#!/bin/bash

# Script de deploy da infraestrutura AWS
echo "=== Deploy do Pipeline Bovespa ==="

# Verificar se AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Erro: AWS CLI não configurado. Execute 'aws configure' primeiro."
    exit 1
fi

# Navegar para diretório de infraestrutura
cd infrastructure

# Inicializar Terraform
echo "Inicializando Terraform..."
terraform init

# Validar configuração
echo "Validando configuração..."
terraform validate

# Planejar deploy
echo "Planejando deploy..."
terraform plan -out=tfplan

# Confirmar deploy
read -p "Deseja continuar com o deploy? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executando deploy..."
    terraform apply tfplan
    
    echo "Deploy concluído!"
    echo "Verificando recursos criados..."
    terraform output
else
    echo "Deploy cancelado."
    rm -f tfplan
fi
