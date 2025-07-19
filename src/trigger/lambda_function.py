import json
import boto3
import logging
from datetime import datetime
import urllib.parse
import os

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente do AWS Glue
glue_client = boto3.client('glue')

def lambda_handler(event, context):
    """
    Lambda acionada pelo S3 quando um novo arquivo parquet é carregado
    Inicia o job do Glue para processamento ETL
    
    Args:
        event: Evento do S3 com informações do arquivo
        context: Contexto de execução do Lambda
        
    Returns:
        Resposta com status da execução
    """
    try:
        # Obter configurações do ambiente
        glue_job_name = os.environ.get('GLUE_JOB_NAME', 'bovespa-etl-job')
        
        logger.info("Iniciando processamento do evento S3")
        
        # Processar cada registro do evento S3
        for record in event['Records']:
            # Extrair informações do S3
            bucket_name = record['s3']['bucket']['name']
            object_key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
            
            logger.info(f"Arquivo detectado: s3://{bucket_name}/{object_key}")
            
            # Verificar se é um arquivo de dados brutos
            if not object_key.startswith('raw-data/bovespa/') or not object_key.endswith('.parquet'):
                logger.info(f"Arquivo ignorado (não é dado bruto): {object_key}")
                continue
            
            # Extrair data do caminho do arquivo
            try:
                # Formato: raw-data/bovespa/year=2025/month=01/day=19/ibov_carteira_20250119.parquet
                path_parts = object_key.split('/')
                year = path_parts[2].split('=')[1]
                month = path_parts[3].split('=')[1]
                day = path_parts[4].split('=')[1]
                processing_date = f"{year}-{month}-{day}"
            except (IndexError, ValueError) as e:
                logger.error(f"Erro ao extrair data do caminho: {e}")
                continue
            
            # Parâmetros para o job Glue
            job_arguments = {
                '--source_bucket': bucket_name,
                '--source_key': object_key,
                '--target_bucket': bucket_name,
                '--processing_date': processing_date,
                '--job-bookmark-option': 'job-bookmark-enable',
                '--enable-metrics': '',
                '--enable-continuous-cloudwatch-log': 'true'
            }
            
            # Gerar nome único para o job run
            job_run_name = f"bovespa-etl-{processing_date.replace('-', '')}-{int(datetime.now().timestamp())}"
            
            logger.info(f"Iniciando job Glue: {glue_job_name}")
            logger.info(f"Job run name: {job_run_name}")
            logger.info(f"Argumentos: {job_arguments}")
            
            # Iniciar job Glue
            response = glue_client.start_job_run(
                JobName=glue_job_name,
                Arguments=job_arguments,
                JobRunId=job_run_name,
                AllocatedCapacity=2,  # Número de DPUs
                Timeout=60,  # Timeout em minutos
                MaxConcurrentRuns=1
            )
            
            job_run_id = response['JobRunId']
            
            logger.info(f"Job Glue iniciado com sucesso. Job Run ID: {job_run_id}")
            
            # Log para CloudWatch
            logger.info({
                'event': 'GLUE_JOB_STARTED',
                'job_name': glue_job_name,
                'job_run_id': job_run_id,
                'source_file': f"s3://{bucket_name}/{object_key}",
                'processing_date': processing_date,
                'timestamp': datetime.now().isoformat()
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Jobs Glue iniciados com sucesso',
                'processed_files': len(event['Records']),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar evento S3: {str(e)}")
        
        # Log de erro estruturado
        logger.error({
            'event': 'LAMBDA_ERROR',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            's3_event': event
        })
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

def get_job_status(job_name: str, job_run_id: str) -> dict:
    """
    Verifica o status de um job Glue
    
    Args:
        job_name: Nome do job Glue
        job_run_id: ID da execução do job
        
    Returns:
        Informações do status do job
    """
    try:
        response = glue_client.get_job_run(
            JobName=job_name,
            RunId=job_run_id
        )
        
        return {
            'job_run_id': job_run_id,
            'job_run_state': response['JobRun']['JobRunState'],
            'started_on': response['JobRun'].get('StartedOn'),
            'completed_on': response['JobRun'].get('CompletedOn'),
            'execution_time': response['JobRun'].get('ExecutionTime'),
            'error_message': response['JobRun'].get('ErrorMessage')
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do job: {e}")
        return {'error': str(e)}

# Para teste local
if __name__ == "__main__":
    # Simular evento S3
    test_event = {
        'Records': [
            {
                's3': {
                    'bucket': {
                        'name': 'bovespa-pipeline-bucket'
                    },
                    'object': {
                        'key': 'raw-data/bovespa/year=2025/month=01/day=19/ibov_carteira_20250119.parquet'
                    }
                }
            }
        ]
    }
    
    os.environ['GLUE_JOB_NAME'] = 'bovespa-etl-job'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
