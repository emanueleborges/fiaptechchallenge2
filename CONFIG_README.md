# Sistema de Configuração com .env

Este projeto agora utiliza um arquivo `.env` para centralizar todas as configurações da AWS e outros parâmetros do sistema.

## 📁 Arquivos de Configuração

- **`.env`** - Arquivo principal com suas configurações (não versionado)
- **`.env.example`** - Template com exemplo das variáveis necessárias
- **`config.py`** - Módulo Python para gerenciar as configurações

## 🚀 Configuração Rápida

### 1. Configurar Credenciais AWS

Execute o script de configuração interativo:

```bash
python configure_aws.py
```

Este script irá:
- Solicitar suas credenciais AWS
- Criar o arquivo `.env` com suas configurações
- Opcionalmente criar o arquivo `~/.aws/credentials`

### 2. Testar Conexão

```bash
python configure_aws.py test
```

## 📋 Variáveis Disponíveis

### Configurações AWS
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

### Configurações S3
```env
S3_BUCKET_NAME=bovespa-pipeline-bucket
S3_RAW_DATA_PREFIX=raw-data/bovespa/
S3_REFINED_DATA_PREFIX=refined-data/bovespa/
S3_AGGREGATED_DATA_PREFIX=refined-data/bovespa-aggregated/
```

### Configurações Lambda
```env
LAMBDA_SCRAPER_FUNCTION_NAME=bovespa-scraper
LAMBDA_TRIGGER_FUNCTION_NAME=bovespa-trigger
LAMBDA_ROLE_NAME=lambda-bovespa-role
```

### Configurações Glue
```env
GLUE_JOB_NAME=bovespa-data-processor
GLUE_ROLE_NAME=GlueServiceRole
```

### Configurações da API
```env
API_PORT=8000
API_HOST=0.0.0.0
```

## 💻 Uso no Código

### Importando Configurações

```python
from config import config

# Acessar configurações
bucket_name = config.s3_bucket_name
region = config.aws_region
api_port = config.api_port

# Validar configurações AWS
if config.validate_aws_config():
    print("✅ Configurações AWS válidas")

# Obter parâmetros para boto3
session_kwargs = config.get_boto3_session_kwargs()
s3_client = boto3.client('s3', **session_kwargs)
```

### Exemplo de Uso nos Lambda Functions

```python
import os
import sys

# Adicionar path para importar config
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from config import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

def lambda_handler(event, context):
    # Obter configurações
    if CONFIG_AVAILABLE:
        bucket_name = config.s3_bucket_name
        glue_job_name = config.glue_job_name
    else:
        # Fallback para variáveis de ambiente
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        glue_job_name = os.environ.get('GLUE_JOB_NAME')
```

## 🔧 Configuração Manual

Se preferir configurar manualmente, copie o arquivo `.env.example` para `.env` e edite os valores:

```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 📦 Dependências

O sistema utiliza a biblioteca `python-dotenv` que já está incluída no `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 🔒 Segurança

- O arquivo `.env` está no `.gitignore` e não será versionado
- Nunca commite credenciais reais no repositório
- Use o arquivo `.env.example` como template sem valores reais

## ✅ Validação

Todas as aplicações agora validam as configurações antes de executar:

- **API Server** (`api_server.py`) - Usa configurações de porta e host
- **Main Pipeline** (`main.py`) - Usa configurações de bucket S3
- **Lambda Functions** - Usam todas as configurações AWS
- **Deploy Scripts** - Usam configurações de deploy e IAM

## 🚀 Como Usar

1. **Configure suas credenciais:**
   ```bash
   python configure_aws.py
   ```

2. **Execute o pipeline local:**
   ```bash
   python main.py
   ```

3. **Inicie a API:**
   ```bash
   python api_server.py
   ```

4. **Faça deploy na AWS:**
   ```bash
   python deploy_lambda.py
   ```

Todas as aplicações agora usarão automaticamente as configurações do arquivo `.env`!
