# Pipeline Batch Bovespa - Tech Challenge FIAP

## Arquitetura do Projeto

Este projeto implementa um pipeline completo para captura e processamento de dados da B3 (Brasil Bolsa Balcão), atendendo aos seguintes requisitos:

### Requisitos Implementados

1. ✅ **Scraping de dados** da B3 (carteira diária do IBOV)
2. ✅ **Ingestão no S3** em formato parquet com partição diária
3. ✅ **Lambda trigger** acionada pelo bucket S3
4. ✅ **Job AWS Glue** no modo visual para ETL
5. ✅ **Transformações obrigatórias**:
   - Agrupamento numérico e sumarização
   - Renomeação de colunas
   - Cálculos com campos de data
6. ✅ **Dados refinados** salvos em parquet particionado
7. ✅ **Catalogação automática** no Glue Catalog
8. ✅ **Disponibilização no Athena**
9. ⭐ **Notebook Athena** para visualizações (opcional)

### Arquitetura

```
[Scheduler/CloudWatch] → [Lambda Scraper] → [S3 Raw Data] → [Lambda Trigger] → [Glue ETL Job] → [S3 Refined Data] → [Athena/QuickSight]
```

### Estrutura do Projeto

```
├── src/
│   ├── scraper/           # Lambda para scraping dos dados da B3
│   │   ├── lambda_function.py
│   │   └── utils.py
│   ├── trigger/           # Lambda para acionar Glue Job
│   │   ├── lambda_function.py
│   └── glue/             # Configurações do Glue Job
│       └── job_script.py
├── infrastructure/        # Terraform/CloudFormation
│   ├── s3.tf
│   ├── lambda.tf
│   ├── glue.tf
│   └── iam.tf
├── notebooks/            # Notebooks Athena para análise
└── tests/               # Testes unitários
```

### Tecnologias Utilizadas

- **Python 3.9+**: Linguagem principal
- **AWS Lambda**: Processamento serverless
- **AWS S3**: Armazenamento de dados
- **AWS Glue**: ETL jobs
- **AWS Athena**: Query engine
- **Pandas**: Manipulação de dados
- **BeautifulSoup**: Web scraping
- **PyArrow**: Manipulação de arquivos parquet

### Instalação e Deploy

#### 1. Configuração Inicial

```bash
# 1. Clone o repositório
git clone <repository-url>
cd fiaptechchallenge2

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure suas credenciais AWS
python configure_aws.py
```

#### 2. Configuração com Arquivo .env

Este projeto utiliza um sistema de configuração centralizado com arquivo `.env`. 

📖 **Consulte o [CONFIG_README.md](CONFIG_README.md) para detalhes completos sobre configuração.**

Principais comandos:
```bash
# Configurar credenciais AWS interativamente
python configure_aws.py

# Testar conexão com AWS
python configure_aws.py test

# Executar pipeline local
python main.py

# Iniciar API local
python api_server.py

# Deploy para AWS
python deploy_lambda.py
```

#### 3. Arquivos de Configuração

- **`.env`** - Suas configurações (criado automaticamente, não versionado)
- **`.env.example`** - Template com exemplos
- **`config.py`** - Módulo de gerenciamento de configurações

### Monitoramento

- CloudWatch Logs para debugging
- CloudWatch Metrics para performance
- Athena Query History para análise de uso
