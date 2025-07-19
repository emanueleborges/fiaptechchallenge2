#!/usr/bin/env python3
"""
Script de Deploy das Lambdas na AWS
Faz deploy das funções Lambda usando boto3
"""

import boto3
import json
import zipfile
import os
import time
from pathlib import Path
from datetime import datetime

# Carregar configurações
try:
    from config import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

class LambdaDeployer:
    def __init__(self):
        if CONFIG_AVAILABLE:
            # Usar configurações do .env
            session_kwargs = config.get_boto3_session_kwargs()
            self.lambda_client = boto3.client('lambda', **session_kwargs)
            self.iam_client = boto3.client('iam', **session_kwargs)
            self.s3_client = boto3.client('s3', **session_kwargs)
            self.account_id = boto3.client('sts', **session_kwargs).get_caller_identity()['Account']
            self.region = config.aws_region
            self.s3_bucket_name = config.s3_bucket_name
            self.lambda_role_name = config.lambda_role_name
        else:
            # Fallback para configurações padrão
            self.lambda_client = boto3.client('lambda')
            self.iam_client = boto3.client('iam')
            self.s3_client = boto3.client('s3')
            self.account_id = boto3.client('sts').get_caller_identity()['Account']
            self.region = boto3.Session().region_name or 'us-east-1'
            self.s3_bucket_name = 'bovespa-pipeline-bucket'
            self.lambda_role_name = 'lambda-bovespa-role'
        
    def create_lambda_role(self, role_name, assume_role_policy, policy_document):
        """Cria role IAM para Lambda"""
        try:
            # Criar role
            self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy)
            )
            print(f"✅ Role {role_name} criada")
            
            # Anexar política
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-policy",
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"✅ Política anexada ao role {role_name}")
            
            # Aguardar propagação do role (importante para Lambda)
            print(f"⏳ Aguardando propagação do role {role_name}...")
            time.sleep(10)
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"⚠️ Role {role_name} já existe")
        
        return f"arn:aws:iam::{self.account_id}:role/{role_name}"
    
    def create_zip_package(self, source_dir, output_file):
        """Cria pacote ZIP para Lambda"""
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            source_path = Path(source_dir)
            
            # Adicionar arquivo principal
            lambda_file = source_path / "lambda_function.py"
            if lambda_file.exists():
                zipf.write(lambda_file, "lambda_function.py")
            
            # Adicionar requirements se existir
            req_file = source_path / "requirements.txt"
            if req_file.exists():
                zipf.write(req_file, "requirements.txt")
        
        print(f"✅ Pacote ZIP criado: {output_file}")
        return output_file
    
    def deploy_scraper_lambda(self):
        """Deploy da Lambda de Scraper"""
        print("🚀 Deployando Lambda Scraper...")
        
        # Criar role IAM
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        scraper_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": "arn:aws:s3:::bovespa-pipeline-*/*"
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket"],
                    "Resource": "arn:aws:s3:::bovespa-pipeline-*"
                }
            ]
        }
        
        role_arn = self.create_lambda_role("bovespa-scraper-role", assume_role_policy, scraper_policy)
        
        # Criar pacote ZIP
        zip_file = self.create_zip_package("src/scraper", "scraper_lambda.zip")
        
        # Deploy da Lambda
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        try:
            response = self.lambda_client.create_function(
                FunctionName='bovespa-scraper',
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Scraper de dados da B3',
                Timeout=300,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'BUCKET_NAME': 'bovespa-pipeline-raw',
                        'ENVIRONMENT': 'production'
                    }
                }
            )
            print(f"✅ Lambda Scraper deployada: {response['FunctionArn']}")
            
        except self.lambda_client.exceptions.ResourceConflictException:
            # Atualizar função existente
            response = self.lambda_client.update_function_code(
                FunctionName='bovespa-scraper',
                ZipFile=zip_content
            )
            print(f"✅ Lambda Scraper atualizada: {response['FunctionArn']}")
        
        # Limpar arquivo ZIP
        os.remove(zip_file)
        
        return response['FunctionArn']
    
    def deploy_trigger_lambda(self):
        """Deploy da Lambda de Trigger"""
        print("🚀 Deployando Lambda Trigger...")
        
        # Criar role IAM
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        trigger_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "glue:StartJobRun",
                        "glue:GetJobRun",
                        "glue:GetJob"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::bovespa-pipeline-*/*"
                }
            ]
        }
        
        role_arn = self.create_lambda_role("bovespa-trigger-role", assume_role_policy, trigger_policy)
        
        # Criar pacote ZIP
        zip_file = self.create_zip_package("src/trigger", "trigger_lambda.zip")
        
        # Deploy da Lambda
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        try:
            response = self.lambda_client.create_function(
                FunctionName='bovespa-glue-trigger',
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Trigger para Glue ETL Job',
                Timeout=60,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'GLUE_JOB_NAME': 'bovespa-etl-job',
                        'ENVIRONMENT': 'production'
                    }
                }
            )
            print(f"✅ Lambda Trigger deployada: {response['FunctionArn']}")
            
        except self.lambda_client.exceptions.ResourceConflictException:
            # Atualizar função existente
            response = self.lambda_client.update_function_code(
                FunctionName='bovespa-glue-trigger',
                ZipFile=zip_content
            )
            print(f"✅ Lambda Trigger atualizada: {response['FunctionArn']}")
        
        # Limpar arquivo ZIP
        os.remove(zip_file)
        
        return response['FunctionArn']
    
    def create_s3_buckets(self):
        """Cria buckets S3 necessários"""
        buckets = [
            'bovespa-pipeline-raw',
            'bovespa-pipeline-refined',
            'bovespa-pipeline-glue-scripts'
        ]
        
        for bucket_name in buckets:
            try:
                # Verificar se bucket já existe
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"⚠️ Bucket {bucket_name} já existe")
                
            except self.s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # Bucket não existe, criar
                    try:
                        if self.region == 'us-east-1':
                            self.s3_client.create_bucket(Bucket=bucket_name)
                        else:
                            self.s3_client.create_bucket(
                                Bucket=bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': self.region}
                            )
                        print(f"✅ Bucket {bucket_name} criado")
                        
                        # Configurar versionamento
                        self.s3_client.put_bucket_versioning(
                            Bucket=bucket_name,
                            VersioningConfiguration={'Status': 'Enabled'}
                        )
                        
                    except Exception as create_error:
                        print(f"❌ Erro ao criar bucket {bucket_name}: {create_error}")
    
    def setup_cloudwatch_schedule(self, lambda_arn):
        """Configura agendamento no CloudWatch Events"""
        events_client = boto3.client('events')
        
        # Criar regra de agendamento (diário às 9h)
        rule_name = 'bovespa-daily-scraper'
        
        try:
            events_client.put_rule(
                Name=rule_name,
                ScheduleExpression='cron(0 9 * * ? *)',  # 9:00 AM UTC todos os dias
                Description='Execução diária do scraper Bovespa',
                State='ENABLED'
            )
            
            # Adicionar Lambda como target
            events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': '1',
                        'Arn': lambda_arn,
                        'Input': json.dumps({'scheduled': True})
                    }
                ]
            )
            
            # Dar permissão ao CloudWatch para invocar Lambda
            self.lambda_client.add_permission(
                FunctionName='bovespa-scraper',
                StatementId='allow-cloudwatch',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=f'arn:aws:events:{self.region}:{self.account_id}:rule/{rule_name}'
            )
            
            print(f"✅ Agendamento configurado: {rule_name}")
            
        except Exception as e:
            print(f"❌ Erro ao configurar agendamento: {e}")
    
    def deploy_all(self):
        """Deploy completo da infraestrutura"""
        print("=" * 60)
        print("🚀 INICIANDO DEPLOY DAS LAMBDAS BOVESPA")
        print("=" * 60)
        print(f"📍 Conta AWS: {self.account_id}")
        print(f"📍 Região: {self.region}")
        print("-" * 60)
        
        try:
            # 1. Criar buckets S3
            print("1️⃣ Criando buckets S3...")
            self.create_s3_buckets()
            print()
            
            # 2. Deploy Lambda Scraper
            print("2️⃣ Deployando Lambda Scraper...")
            scraper_arn = self.deploy_scraper_lambda()
            print()
            
            # 3. Deploy Lambda Trigger
            print("3️⃣ Deployando Lambda Trigger...")
            trigger_arn = self.deploy_trigger_lambda()
            print()
            
            # 4. Configurar agendamento
            print("4️⃣ Configurando agendamento...")
            self.setup_cloudwatch_schedule(scraper_arn)
            print()
            
            # 5. Resumo final
            print("=" * 60)
            print("✅ DEPLOY CONCLUÍDO COM SUCESSO!")
            print("=" * 60)
            print(f"🔗 Lambda Scraper: {scraper_arn}")
            print(f"🔗 Lambda Trigger: {trigger_arn}")
            print("📅 Agendamento: Diário às 9:00 AM UTC")
            print("💡 Para testar, execute o scraper manualmente no Console AWS")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ ERRO NO DEPLOY: {e}")
            print("🔍 Verifique as permissões da sua conta AWS")

if __name__ == "__main__":
    deployer = LambdaDeployer()
    deployer.deploy_all()
