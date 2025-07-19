#!/usr/bin/env python3
"""
Script para configurar credenciais AWS usando arquivo .env
"""

import os
from pathlib import Path

def configure_aws_credentials():
    """Configura credenciais AWS no arquivo .env"""
    
    print("🔐 CONFIGURAÇÃO DE CREDENCIAIS AWS")
    print("=" * 50)
    
    # Obter inputs do usuário
    access_key = input("Digite seu AWS Access Key ID: ").strip()
    secret_key = input("Digite seu AWS Secret Access Key: ").strip()
    region = input("Digite sua região AWS (ex: us-east-1, sa-east-1): ").strip() or "us-east-1"
    bucket_name = input("Digite o nome do bucket S3 (padrão: bovespa-pipeline-bucket): ").strip() or "bovespa-pipeline-bucket"
    
    # Verificar se arquivo .env existe
    project_root = Path(__file__).parent
    env_file = project_root / '.env'
    
    if env_file.exists():
        print(f"✅ Atualizando arquivo .env existente: {env_file}")
        _update_existing_env_file(env_file, access_key, secret_key, region, bucket_name)
    else:
        print(f"📝 Criando arquivo .env: {env_file}")
        _create_new_env_file(env_file, access_key, secret_key, region, bucket_name)
    
    print("✅ Configurações AWS salvas no arquivo .env")
    
    # Também criar/atualizar credenciais AWS tradicionais (opcional)
    create_aws_credentials = input("\nDeseja também criar o arquivo ~/.aws/credentials? (s/N): ").strip().lower()
    
    if create_aws_credentials in ['s', 'sim', 'y', 'yes']:
        _create_aws_credentials_file(access_key, secret_key, region)
    
    print("\n🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("💡 As configurações estão no arquivo .env na raiz do projeto")
    print("💡 Use 'python main.py' para testar o pipeline localmente")
    print("💡 Use 'python api_server.py' para iniciar a API")


def _update_existing_env_file(env_file, access_key, secret_key, region, bucket_name):
    """Atualiza arquivo .env existente"""
    # Ler arquivo existente
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Atualizar variáveis
    updated_lines = []
    updated_vars = set()
    
    for line in lines:
        if line.startswith('AWS_ACCESS_KEY_ID='):
            updated_lines.append(f'AWS_ACCESS_KEY_ID={access_key}\n')
            updated_vars.add('AWS_ACCESS_KEY_ID')
        elif line.startswith('AWS_SECRET_ACCESS_KEY='):
            updated_lines.append(f'AWS_SECRET_ACCESS_KEY={secret_key}\n')
            updated_vars.add('AWS_SECRET_ACCESS_KEY')
        elif line.startswith('AWS_REGION='):
            updated_lines.append(f'AWS_REGION={region}\n')
            updated_vars.add('AWS_REGION')
        elif line.startswith('S3_BUCKET_NAME='):
            updated_lines.append(f'S3_BUCKET_NAME={bucket_name}\n')
            updated_vars.add('S3_BUCKET_NAME')
        else:
            updated_lines.append(line)
    
    # Adicionar variáveis que não existiam
    vars_to_add = {
        'AWS_ACCESS_KEY_ID': access_key,
        'AWS_SECRET_ACCESS_KEY': secret_key,
        'AWS_REGION': region,
        'S3_BUCKET_NAME': bucket_name
    }
    
    for var_name, var_value in vars_to_add.items():
        if var_name not in updated_vars:
            updated_lines.append(f'{var_name}={var_value}\n')
    
    # Escrever arquivo atualizado
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)


def _create_new_env_file(env_file, access_key, secret_key, region, bucket_name):
    """Cria novo arquivo .env baseado no template"""
    env_content = f"""# Configurações AWS
AWS_REGION={region}
AWS_ACCESS_KEY_ID={access_key}
AWS_SECRET_ACCESS_KEY={secret_key}

# S3 Configuration
S3_BUCKET_NAME={bucket_name}
S3_RAW_DATA_PREFIX=raw-data/bovespa/
S3_REFINED_DATA_PREFIX=refined-data/bovespa/
S3_AGGREGATED_DATA_PREFIX=refined-data/bovespa-aggregated/

# Glue Configuration
GLUE_JOB_NAME=bovespa-data-processor
GLUE_ROLE_NAME=GlueServiceRole

# Lambda Configuration
LAMBDA_SCRAPER_FUNCTION_NAME=bovespa-scraper
LAMBDA_TRIGGER_FUNCTION_NAME=bovespa-trigger
LAMBDA_ROLE_NAME=lambda-bovespa-role

# Terraform Configuration
PROJECT_NAME=bovespa-pipeline
ENVIRONMENT=dev

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)


def _create_aws_credentials_file(access_key, secret_key, region):
    """Cria arquivos de credenciais AWS tradicionais"""
    # Criar diretório .aws se não existir
    aws_dir = Path.home() / ".aws"
    aws_dir.mkdir(exist_ok=True)
    
    # Criar arquivo de credenciais
    credentials_file = aws_dir / "credentials"
    with open(credentials_file, 'w') as f:
        f.write(f"""[default]
aws_access_key_id = {access_key}
aws_secret_access_key = {secret_key}
""")

    # Criar arquivo de configuração
    config_file = aws_dir / "config"
    with open(config_file, 'w') as f:
        f.write(f"""[default]
region = {region}
""")
    
    print(f"✅ Credenciais AWS também salvas em: {aws_dir}")


def test_aws_connection():
    """Testa a conexão com AWS usando as configurações do .env"""
    try:
        from config import config
        
        # Validar configurações
        if not config.validate_aws_config():
            return False
        
        # Testar conexão
        import boto3
        session_kwargs = config.get_boto3_session_kwargs()
        
        # Testar S3
        s3_client = boto3.client('s3', **session_kwargs)
        response = s3_client.list_buckets()
        
        print("✅ Conexão com AWS estabelecida com sucesso!")
        print(f"🪣 Buckets encontrados: {len(response.get('Buckets', []))}")
        return True
        
    except ImportError:
        print("❌ Módulo config não encontrado. Execute 'pip install -r requirements.txt'")
        return False
    except Exception as e:
        print(f"❌ Erro ao conectar com AWS: {str(e)}")
        print("💡 Verifique suas credenciais no arquivo .env")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_aws_connection()
    else:
        configure_aws_credentials()
