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
│   │   ├── requirements.txt
│   │   └── utils.py
│   ├── trigger/           # Lambda para acionar Glue Job
│   │   ├── lambda_function.py
│   │   └── requirements.txt
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

1. Clone o repositório
2. Configure as credenciais AWS
3. Execute o deploy da infraestrutura
4. Agende o scraper para execução diária

### Monitoramento

- CloudWatch Logs para debugging
- CloudWatch Metrics para performance
- Athena Query History para análise de uso
