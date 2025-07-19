#!/usr/bin/env python3
"""
Pipeline Bovespa - Aplicação Principal
Executa o scraping dos dados da B3 e demonstra todas as funcionalidades
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório src ao path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Importações locais
try:
    from scraper.b3_scraper_local import B3Scraper
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("📁 Certifique-se de que os arquivos estão na estrutura correta")
    sys.exit(1)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bovespa_pipeline.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Função principal da aplicação"""
    print("🚀 Iniciando Pipeline Bovespa...")
    print("=" * 60)
    
    try:
        # 1. Configurar scraper
        print("📡 1. Configurando Web Scraper...")
        scraper = B3Scraper("bovespa-test-bucket")  # Bucket fictício para teste local
        
        # 2. Fazer scraping dos dados
        print("🔄 2. Fazendo scraping dos dados da B3...")
        dados_bovespa = scraper.fetch_ibov_data()
        
        if not dados_bovespa:
            print("❌ Nenhum dado foi obtido do scraping")
            return
        
        print(f"✅ {len(dados_bovespa)} registros obtidos com sucesso!")
        
        # 3. Mostrar amostra dos dados
        print("📊 3. Amostra dos dados obtidos:")
        print("-" * 80)
        
        import pandas as pd
        df = pd.DataFrame(dados_bovespa)
        
        # Mostrar estatísticas básicas
        print(f"📈 Total de ações: {len(df)}")
        print(f"💰 Participação total: {df['percentual_participacao'].sum():.2f}%")
        print(f"🏆 Maior participação: {df['percentual_participacao'].max():.2f}%")
        print(f"📅 Data do pregão: {df['data_pregao'].iloc[0] if not df.empty else 'N/A'}")
        
        # Top 10 ações
        print("\n🏆 TOP 10 AÇÕES POR PARTICIPAÇÃO:")
        print("-" * 80)
        top_10 = df.nlargest(10, 'percentual_participacao')
        
        for i, row in top_10.iterrows():
            print(f"{row['codigo_acao']:>6} - {row['nome_empresa']:<25} - {row['percentual_participacao']:>6.3f}% - {row['tipo_acao']}")
        
        # 4. Salvar dados localmente
        print("\n💾 4. Salvando dados localmente...")
        
        # Salvar CSV
        csv_filename = f"bovespa_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"✅ Dados salvos em: {csv_filename}")
        
        # Salvar JSON
        json_filename = f"bovespa_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(dados_bovespa, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ Dados salvos em: {json_filename}")
        
        # 5. Análise por tipo de ação
        print("\n📊 5. Análise por tipo de ação:")
        print("-" * 50)
        
        tipos_analise = df.groupby('tipo_acao').agg({
            'codigo_acao': 'count',
            'percentual_participacao': ['sum', 'mean', 'max']
        }).round(3)
        
        tipos_analise.columns = ['Quantidade', 'Participação_Total', 'Participação_Média', 'Maior_Participação']
        print(tipos_analise)
        
        # 6. Teste de conversão Parquet (se pyarrow estiver disponível)
        try:
            parquet_filename = f"bovespa_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            df.to_parquet(parquet_filename, index=False)
            print(f"✅ Dados salvos em formato Parquet: {parquet_filename}")
        except ImportError:
            print("⚠️ PyArrow não disponível - pulando conversão Parquet")
        
        print("\n🎉 Pipeline executado com sucesso!")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Execução interrompida pelo usuário")
        return False
    except Exception as e:
        logger.error(f"Erro na execução do pipeline: {e}")
        print(f"❌ Erro: {e}")
        return False

def test_components():
    """Testa componentes individuais"""
    print("🧪 Testando componentes do pipeline...")
    
    try:
        # Teste do scraper
        print("🔄 Testando scraper...")
        scraper = B3Scraper("test-bucket")
        
        # Teste de parsing de números
        test_numbers = ["1.234.567,89", "123,45", "1.000"]
        for num in test_numbers:
            parsed = scraper._parse_number(num)
            print(f"   {num} -> {parsed}")
        
        print("✅ Componentes testados com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes: {e}")
        return False

def show_help():
    """Mostra ajuda de uso"""
    print("📚 Ajuda - Pipeline Bovespa")
    print("=" * 40)
    print("Uso: python main.py [opção]")
    print()
    print("Opções:")
    print("  (sem argumentos)  - Executa pipeline completo")
    print("  --test           - Executa testes dos componentes")
    print("  --help           - Mostra esta ajuda")
    print()
    print("Funcionalidades:")
    print("  • Web scraping do site da B3")
    print("  • Processamento dos dados do IBOV")
    print("  • Análises estatísticas básicas")
    print("  • Export para CSV, JSON e Parquet")
    print("  • Logs detalhados de execução")

if __name__ == "__main__":
    # Processar argumentos da linha de comando
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h', 'help']:
            show_help()
        elif arg in ['--test', '-t', 'test']:
            test_components()
        else:
            print(f"❌ Argumento desconhecido: {arg}")
            show_help()
    else:
        # Executar pipeline principal
        success = main()
        sys.exit(0 if success else 1)
