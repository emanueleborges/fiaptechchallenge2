import json
import boto3
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import logging
from typing import Dict, List, Optional
import re

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
s3_client = boto3.client('s3')

class B3Scraper:
    """
    Classe responsável pelo scraping de dados da B3 (Brasil Bolsa Balcão)
    Captura dados da carteira diária do IBOV
    """
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.base_url = "https://sistemaswebb3-listados.b3.com.br/indexPage/day/IBOV"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def fetch_ibov_data(self, date_str: Optional[str] = None) -> List[Dict]:
        """
        Faz o scraping dos dados da carteira do IBOV
        
        Args:
            date_str: Data no formato YYYY-MM-DD, se None usa data atual
            
        Returns:
            Lista de dicionários com os dados das ações
        """
        try:
            params = {
                'language': 'pt-br'
            }
            
            if date_str:
                params['date'] = date_str
            
            logger.info(f"Fazendo scraping da URL: {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Encontrar a tabela com os dados
            table_rows = soup.find_all('tr')
            
            stocks_data = []
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            for row in table_rows:
                cells = row.find_all('td')
                if len(cells) >= 5:  # Linha com dados válidos
                    try:
                        # Extrair dados das células
                        codigo = cells[0].text.strip() if cells[0].text.strip() else None
                        nome_empresa = cells[1].text.strip() if cells[1].text.strip() else None
                        tipo = cells[2].text.strip() if cells[2].text.strip() else None
                        qtde_teorica = cells[3].text.strip() if cells[3].text.strip() else None
                        participacao = cells[4].text.strip() if cells[4].text.strip() else None
                        
                        # Validar se temos dados válidos
                        if not codigo or len(codigo) < 4:
                            continue
                            
                        # Limpar e converter dados numéricos
                        if qtde_teorica:
                            qtde_teorica = qtde_teorica.replace('.', '').replace(',', '.')
                            try:
                                qtde_teorica = float(qtde_teorica)
                            except ValueError:
                                qtde_teorica = None
                        
                        if participacao:
                            participacao = participacao.replace(',', '.')
                            try:
                                participacao = float(participacao)
                            except ValueError:
                                participacao = None
                        
                        stock_data = {
                            'data_pregao': current_date,
                            'codigo_acao': codigo,
                            'nome_empresa': nome_empresa,
                            'tipo_acao': tipo,
                            'quantidade_teorica': qtde_teorica,
                            'percentual_participacao': participacao,
                            'data_extracao': datetime.now().isoformat(),
                            'fonte': 'B3_IBOV'
                        }
                        
                        stocks_data.append(stock_data)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao processar linha da tabela: {e}")
                        continue
            
            logger.info(f"Extraídos {len(stocks_data)} registros de ações")
            return stocks_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao fazer request para B3: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro no scraping dos dados: {e}")
            raise
    
    def save_to_s3_parquet(self, data: List[Dict], date_str: str) -> str:
        """
        Salva os dados no S3 em formato parquet com partição diária
        
        Args:
            data: Lista de dicionários com os dados
            date_str: Data para particionamento
            
        Returns:
            Caminho do arquivo salvo no S3
        """
        try:
            if not data:
                raise ValueError("Nenhum dado para salvar")
            
            # Criar DataFrame
            df = pd.DataFrame(data)
            
            # Adicionar colunas de particionamento
            df['year'] = pd.to_datetime(df['data_pregao']).dt.year
            df['month'] = pd.to_datetime(df['data_pregao']).dt.month
            df['day'] = pd.to_datetime(df['data_pregao']).dt.day
            
            # Converter para formato parquet em memória
            buffer = BytesIO()
            table = pa.Table.from_pandas(df)
            pq.write_table(table, buffer)
            
            # Definir caminho no S3 com particionamento
            s3_key = f"raw-data/bovespa/year={df['year'].iloc[0]}/month={df['month'].iloc[0]:02d}/day={df['day'].iloc[0]:02d}/ibov_carteira_{date_str.replace('-', '')}.parquet"
            
            # Upload para S3
            buffer.seek(0)
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/octet-stream',
                Metadata={
                    'source': 'B3_SCRAPER',
                    'date': date_str,
                    'records_count': str(len(data)),
                    'extraction_time': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Dados salvos em S3: s3://{self.bucket_name}/{s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Erro ao salvar no S3: {e}")
            raise

def lambda_handler(event, context):
    """
    Handler principal da Lambda para scraping de dados da B3
    
    Args:
        event: Evento do Lambda (pode conter data específica)
        context: Contexto de execução do Lambda
        
    Returns:
        Resposta com status da execução
    """
    try:
        # Obter configurações do ambiente
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("Variável de ambiente S3_BUCKET_NAME não encontrada")
        
        # Determinar data para scraping
        date_str = event.get('date') if event and 'date' in event else datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Iniciando scraping para data: {date_str}")
        
        # Inicializar scraper
        scraper = B3Scraper(bucket_name)
        
        # Fazer scraping
        stocks_data = scraper.fetch_ibov_data(date_str)
        
        if not stocks_data:
            logger.warning("Nenhum dado encontrado no scraping")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'Nenhum dado encontrado',
                    'date': date_str
                })
            }
        
        # Salvar no S3
        s3_path = scraper.save_to_s3_parquet(stocks_data, date_str)
        
        # Resposta de sucesso
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scraping executado com sucesso',
                'date': date_str,
                'records_count': len(stocks_data),
                's3_path': s3_path,
                'execution_time': datetime.now().isoformat()
            })
        }
        
        logger.info(f"Scraping concluído: {len(stocks_data)} registros processados")
        return response
        
    except Exception as e:
        logger.error(f"Erro na execução do scraping: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'date': date_str if 'date_str' in locals() else 'N/A',
                'execution_time': datetime.now().isoformat()
            })
        }

# Para teste local
if __name__ == "__main__":
    import os
    os.environ['S3_BUCKET_NAME'] = 'bovespa-pipeline-bucket'
    
    test_event = {
        'date': '2025-01-19'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
