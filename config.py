"""
Configuração centralizada do projeto usando arquivo .env
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def load_env_file(env_file: Optional[str] = None) -> None:
    """
    Carrega variáveis de ambiente de um arquivo .env
    
    Args:
        env_file: Caminho para o arquivo .env. Se None, usa .env na raiz do projeto
    """
    if env_file is None:
        project_root = Path(__file__).parent
        env_file_path = project_root / '.env'
    else:
        env_file_path = Path(env_file)
    
    if not env_file_path.exists():
        print(f"⚠️  Arquivo .env não encontrado em: {env_file_path}")
        print("💡 Use o arquivo .env.example como template")
        return
    
    try:
        if DOTENV_AVAILABLE:
            # Usa python-dotenv se disponível
            load_dotenv(dotenv_path=env_file_path, override=False)
            print(f"✅ Arquivo .env carregado com sucesso: {env_file_path}")
        else:
            # Fallback manual se python-dotenv não estiver instalado
            _load_env_manual(env_file_path)
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo .env: {e}")


def _remove_quotes(value: str) -> str:
    """Remove aspas simples ou duplas do valor"""
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_env_line(line: str) -> Optional[tuple]:
    """Parse de uma linha do arquivo .env"""
    line = line.strip()
    # Ignora linhas vazias e comentários
    if not line or line.startswith('#'):
        return None
    
    # Parse da linha KEY=VALUE
    if '=' in line:
        key, value = line.split('=', 1)
        key = key.strip()
        value = _remove_quotes(value.strip())
        return key, value
    
    return None


def _load_env_manual(env_file_path: Path) -> None:
    """Carregamento manual do arquivo .env (fallback)"""
    with open(env_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = _parse_env_line(line)
            if parsed:
                key, value = parsed
                # Define a variável de ambiente se ainda não foi definida
                if key not in os.environ:
                    os.environ[key] = value
    
    print(f"✅ Arquivo .env carregado com sucesso: {env_file_path}")


class Config:
    """Classe para acessar configurações do projeto"""
    
    def __init__(self):
        # Carrega automaticamente o .env quando a classe é instanciada
        load_env_file()
    
    # AWS Configuration
    @property
    def aws_region(self) -> str:
        return os.getenv('AWS_REGION', 'us-east-1')
    
    @property
    def aws_access_key_id(self) -> Optional[str]:
        return os.getenv('AWS_ACCESS_KEY_ID')
    
    @property
    def aws_secret_access_key(self) -> Optional[str]:
        return os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # S3 Configuration
    @property
    def s3_bucket_name(self) -> str:
        return os.getenv('S3_BUCKET_NAME', 'bovespa-pipeline-bucket')
    
    @property
    def s3_raw_data_prefix(self) -> str:
        return os.getenv('S3_RAW_DATA_PREFIX', 'raw-data/bovespa/')
    
    @property
    def s3_refined_data_prefix(self) -> str:
        return os.getenv('S3_REFINED_DATA_PREFIX', 'refined-data/bovespa/')
    
    @property
    def s3_aggregated_data_prefix(self) -> str:
        return os.getenv('S3_AGGREGATED_DATA_PREFIX', 'refined-data/bovespa-aggregated/')
    
    # Glue Configuration
    @property
    def glue_job_name(self) -> str:
        return os.getenv('GLUE_JOB_NAME', 'bovespa-data-processor')
    
    @property
    def glue_role_name(self) -> str:
        return os.getenv('GLUE_ROLE_NAME', 'GlueServiceRole')
    
    # Lambda Configuration
    @property
    def lambda_scraper_function_name(self) -> str:
        return os.getenv('LAMBDA_SCRAPER_FUNCTION_NAME', 'bovespa-scraper')
    
    @property
    def lambda_trigger_function_name(self) -> str:
        return os.getenv('LAMBDA_TRIGGER_FUNCTION_NAME', 'bovespa-trigger')
    
    @property
    def lambda_role_name(self) -> str:
        return os.getenv('LAMBDA_ROLE_NAME', 'lambda-bovespa-role')
    
    # Terraform Configuration
    @property
    def project_name(self) -> str:
        return os.getenv('PROJECT_NAME', 'bovespa-pipeline')
    
    @property
    def environment(self) -> str:
        return os.getenv('ENVIRONMENT', 'dev')
    
    # API Configuration
    @property
    def api_port(self) -> int:
        return int(os.getenv('API_PORT', '8000'))
    
    @property
    def api_host(self) -> str:
        return os.getenv('API_HOST', '0.0.0.0')
    
    def validate_aws_config(self) -> bool:
        """Valida se as configurações AWS estão definidas"""
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION',
            'S3_BUCKET_NAME'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Variáveis de ambiente obrigatórias não encontradas: {', '.join(missing_vars)}")
            print("💡 Configure essas variáveis no arquivo .env")
            return False
        
        return True
    
    def get_boto3_session_kwargs(self) -> dict:
        """Retorna os parâmetros para criar uma sessão boto3"""
        kwargs = {
            'region_name': self.aws_region
        }
        
        # Adiciona credenciais se estiverem definidas no .env
        if self.aws_access_key_id and self.aws_secret_access_key:
            kwargs.update({
                'aws_access_key_id': self.aws_access_key_id,
                'aws_secret_access_key': self.aws_secret_access_key
            })
        
        return kwargs


# Instância global da configuração
config = Config()
