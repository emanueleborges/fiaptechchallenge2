"""
API REST para dados da Bovespa - Versão Local
FastAPI server para servir dados coletados
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

# Importar scraper local
import sys
sys.path.append('src')

from scraper.b3_scraper_local import B3Scraper

# Configurar FastAPI
app = FastAPI(
    title="Bovespa Pipeline API - Local",
    description="API REST para consulta de dados da B3 processados localmente",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cache simples para dados
cached_data = {}
last_update = None

def get_latest_data():
    """Obtém os dados mais recentes (cache ou scraping)"""
    global cached_data, last_update
    
    # Verificar se precisa atualizar (cache de 1 hora)
    if (not cached_data or 
        not last_update or 
        (datetime.now() - last_update).seconds > 3600):
        
        print("🔄 Atualizando dados...")
        scraper = B3Scraper()
        raw_data = scraper.fetch_ibov_data()
        
        if raw_data:
            cached_data = raw_data
            last_update = datetime.now()
            print(f"✅ {len(raw_data)} registros atualizados")
        else:
            print("⚠️ Usando dados em cache")
    
    return cached_data

def load_local_files():
    """Carrega dados dos arquivos locais se disponíveis"""
    current_dir = Path(".")
    
    # Procurar arquivos CSV mais recentes
    csv_files = list(current_dir.glob("bovespa_data_*.csv"))
    
    if csv_files:
        # Pegar o mais recente
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"📂 Carregando dados de: {latest_csv}")
        
        try:
            df = pd.read_csv(latest_csv)
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"❌ Erro ao carregar arquivo: {e}")
    
    return []

@app.get("/")
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "message": "Bovespa Pipeline API - Versão Local",
        "version": "1.0.0",
        "description": "API para consulta de dados da B3 processados localmente",
        "endpoints": {
            "health": "/health",
            "refresh": "/refresh",
            "latest_data": "/api/v1/bovespa/latest",
            "daily_data": "/api/v1/bovespa/daily/{date}",
            "statistics": "/api/v1/bovespa/statistics",
            "top_stocks": "/api/v1/bovespa/top/{limit}",
            "stock_details": "/api/v1/bovespa/stock/{ticker}"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        data_count = len(cached_data) if cached_data else 0
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cached_records": data_count,
            "last_update": last_update.isoformat() if last_update else None,
            "services": {
                "scraper": "available",
                "cache": "active"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/refresh")
async def refresh_data():
    """Força atualização dos dados"""
    global cached_data, last_update
    
    try:
        print("🔄 Forçando atualização dos dados...")
        scraper = B3Scraper()
        raw_data = scraper.fetch_ibov_data()
        
        if raw_data:
            cached_data = raw_data
            last_update = datetime.now()
            
            return {
                "message": "Dados atualizados com sucesso",
                "count": len(raw_data),
                "timestamp": last_update.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao obter dados")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na atualização: {str(e)}")

@app.get("/api/v1/bovespa/latest")
async def get_latest_data_api(limit: int = Query(100, ge=1, le=1000)):
    """Retorna os dados mais recentes da Bovespa"""
    try:
        data = get_latest_data()
        
        if not data:
            # Tentar carregar arquivos locais
            data = load_local_files()
        
        if not data:
            return {"message": "Nenhum dado encontrado", "data": []}
        
        # Limitar resultados
        limited_data = data[:limit]
        
        return {
            "message": "Dados recuperados com sucesso",
            "count": len(limited_data),
            "total_available": len(data),
            "timestamp": datetime.now().isoformat(),
            "data": limited_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/v1/bovespa/statistics")
async def get_market_statistics():
    """Retorna estatísticas do mercado"""
    try:
        data = get_latest_data()
        
        if not data:
            data = load_local_files()
        
        if not data:
            return {"message": "Nenhuma estatística disponível"}
        
        df = pd.DataFrame(data)
        
        stats = {
            "total_acoes": len(df),
            "tipos_unicos": df['tipo_acao'].nunique(),
            "participacao_total": round(df['percentual_participacao'].sum(), 2),
            "participacao_media": round(df['percentual_participacao'].mean(), 3),
            "maior_participacao": round(df['percentual_participacao'].max(), 3),
            "menor_participacao": round(df['percentual_participacao'].min(), 3),
            "ultima_atualizacao": df['data_pregao'].iloc[0] if not df.empty else None
        }
        
        return {
            "message": "Estatísticas recuperadas com sucesso",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/v1/bovespa/top/{limit}")
async def get_top_stocks(limit: int):
    """Retorna as ações com maior participação"""
    try:
        if limit > 100:
            raise HTTPException(status_code=400, detail="Limite máximo é 100")
        
        data = get_latest_data()
        
        if not data:
            data = load_local_files()
        
        if not data:
            return {"message": "Nenhum dado encontrado", "data": []}
        
        # Ordenar por participação
        df = pd.DataFrame(data)
        top_data = df.nlargest(limit, 'percentual_participacao')
        
        return {
            "message": f"Top {limit} ações recuperadas com sucesso",
            "count": len(top_data),
            "data": top_data.to_dict(orient='records')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/v1/bovespa/stock/{ticker}")
async def get_stock_details(ticker: str):
    """Retorna detalhes de uma ação específica"""
    try:
        ticker = ticker.upper()
        
        data = get_latest_data()
        
        if not data:
            data = load_local_files()
        
        if not data:
            return {"message": f"Ação {ticker} não encontrada", "data": []}
        
        # Filtrar por ticker
        df = pd.DataFrame(data)
        stock_data = df[df['codigo_acao'].str.upper() == ticker]
        
        if stock_data.empty:
            return {"message": f"Ação {ticker} não encontrada", "data": []}
        
        return {
            "message": f"Dados da ação {ticker} recuperados com sucesso",
            "ticker": ticker,
            "count": len(stock_data),
            "data": stock_data.to_dict(orient='records')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/v1/bovespa/export/{format}")
async def export_data(format: str):
    """Exporta dados em diferentes formatos"""
    try:
        if format.lower() not in ['json', 'csv']:
            raise HTTPException(status_code=400, detail="Formato suportado: json, csv")
        
        data = get_latest_data()
        
        if not data:
            data = load_local_files()
        
        if not data:
            return {"message": "Nenhum dado disponível para export"}
        
        df = pd.DataFrame(data)
        
        if format.lower() == 'csv':
            filename = f"bovespa_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            return {"message": f"Dados exportados para {filename}"}
        
        else:  # json
            filename = f"bovespa_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return {"message": f"Dados exportados para {filename}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no export: {str(e)}")

if __name__ == "__main__":
    # Carregar dados iniciais
    print("🚀 Iniciando API Bovespa...")
    get_latest_data()
    
    print("🌐 API disponível em:")
    print("   • http://localhost:8000")
    print("   • Documentação: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")
    print()
    print("📊 Endpoints principais:")
    print("   • GET /api/v1/bovespa/latest - Dados mais recentes")
    print("   • GET /api/v1/bovespa/statistics - Estatísticas")
    print("   • GET /api/v1/bovespa/top/10 - Top 10 ações")
    print("   • GET /refresh - Atualizar dados")
    
    # Iniciar servidor
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
