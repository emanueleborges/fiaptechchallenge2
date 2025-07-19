#!/usr/bin/env python3
"""
Script para configurar credenciais AWS manualmente
"""

import os
from pathlib import Path

def configure_aws_credentials():
    """Configura credenciais AWS manualmente"""
    
    print("🔐 CONFIGURAÇÃO DE CREDENCIAIS AWS")
    print("=" * 50)
    
    # Obter inputs do usuário
    access_key = input("Digite seu AWS Access Key ID: ").strip()
    secret_key = input("Digite seu AWS Secret Access Key: ").strip()
    region = input("Digite sua região AWS (ex: us-east-1, sa-east-1): ").strip() or "us-east-1"
    
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
    
    # Criar arquivo de config
    config_file = aws_dir / "config"
    with open(config_file, 'w') as f:
        f.write(f"""[default]
region = {region}
output = json
""")
    
    print(f"✅ Credenciais configuradas!")
    print(f"📁 Arquivos criados em: {aws_dir}")
    print("-" * 50)
    
    # Testar credenciais
    print("🔍 Testando credenciais...")
    
    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print("✅ CREDENCIAIS VÁLIDAS!")
        print(f"👤 Usuário: {identity.get('Arn', 'N/A')}")
        print(f"🏢 Conta: {identity.get('Account', 'N/A')}")
        print(f"🌎 Região: {region}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO nas credenciais: {e}")
        return False

if __name__ == "__main__":
    configure_aws_credentials()
