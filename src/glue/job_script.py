import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime, timedelta
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obter argumentos do job
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_bucket',
    'source_key',
    'target_bucket',
    'processing_date'
])

# Inicializar contextos do Glue
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

logger.info(f"Iniciando job Glue: {args['JOB_NAME']}")
logger.info(f"Processando arquivo: s3://{args['source_bucket']}/{args['source_key']}")

try:
    # ETAPA 1: LEITURA DOS DADOS BRUTOS
    logger.info("=== ETAPA 1: LEITURA DOS DADOS ===")
    
    # Criar DynamicFrame a partir do arquivo parquet no S3
    raw_data_path = f"s3://{args['source_bucket']}/{args['source_key']}"
    
    raw_dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="s3",
        connection_options={
            "paths": [raw_data_path],
            "recurse": True
        },
        format="parquet",
        transformation_ctx="raw_data_source"
    )
    
    logger.info(f"Registros lidos: {raw_dynamic_frame.count()}")
    raw_dynamic_frame.printSchema()
    
    # Converter para DataFrame do Spark para manipulações complexas
    df = raw_dynamic_frame.toDF()
    
    # ETAPA 2: LIMPEZA E VALIDAÇÃO INICIAL
    logger.info("=== ETAPA 2: LIMPEZA DOS DADOS ===")
    
    # Remover registros com código de ação nulo ou inválido
    df_clean = df.filter(
        (F.col("codigo_acao").isNotNull()) & 
        (F.length(F.col("codigo_acao")) >= 4) &
        (F.col("quantidade_teorica").isNotNull()) &
        (F.col("percentual_participacao").isNotNull())
    )
    
    # Adicionar colunas calculadas de data
    df_clean = df_clean.withColumn("data_pregao_date", F.to_date(F.col("data_pregao")))
    df_clean = df_clean.withColumn("data_extracao_timestamp", F.to_timestamp(F.col("data_extracao")))
    
    logger.info(f"Registros após limpeza: {df_clean.count()}")
    
    # ETAPA 3: TRANSFORMAÇÕES OBRIGATÓRIAS
    logger.info("=== ETAPA 3: TRANSFORMAÇÕES OBRIGATÓRIAS ===")
    
    # REQUISITO A: Agrupamento numérico, sumarização e contagem
    logger.info("Aplicando agrupamento e sumarização...")
    
    # Agrupar por tipo de ação e calcular estatísticas
    df_aggregated = df_clean.groupBy("tipo_acao", "data_pregao") \
        .agg(
            F.count("codigo_acao").alias("qtd_acoes_por_tipo"),
            F.sum("quantidade_teorica").alias("quantidade_teorica_total"),
            F.sum("percentual_participacao").alias("participacao_total_tipo"),
            F.avg("percentual_participacao").alias("participacao_media_tipo"),
            F.max("percentual_participacao").alias("maior_participacao_tipo"),
            F.min("percentual_participacao").alias("menor_participacao_tipo")
        )
    
    # REQUISITO B: Renomear duas colunas existentes
    logger.info("Renomeando colunas...")
    
    df_clean_renamed = df_clean \
        .withColumnRenamed("codigo_acao", "ticker_symbol") \
        .withColumnRenamed("nome_empresa", "company_name") \
        .withColumnRenamed("quantidade_teorica", "theoretical_quantity") \
        .withColumnRenamed("percentual_participacao", "participation_percentage")
    
    # REQUISITO C: Cálculos com campos de data
    logger.info("Aplicando cálculos de data...")
    
    # Adicionar colunas com cálculos de data
    df_with_date_calcs = df_clean_renamed \
        .withColumn("dias_desde_extracao", 
                   F.datediff(F.current_date(), F.col("data_pregao_date"))) \
        .withColumn("semana_pregao", 
                   F.weekofyear(F.col("data_pregao_date"))) \
        .withColumn("trimestre_pregao", 
                   F.quarter(F.col("data_pregao_date"))) \
        .withColumn("dia_semana_pregao", 
                   F.dayofweek(F.col("data_pregao_date"))) \
        .withColumn("nome_dia_semana", 
                   F.when(F.col("dia_semana_pregao") == 1, "Domingo")
                   .when(F.col("dia_semana_pregao") == 2, "Segunda-feira")
                   .when(F.col("dia_semana_pregao") == 3, "Terça-feira")
                   .when(F.col("dia_semana_pregao") == 4, "Quarta-feira")
                   .when(F.col("dia_semana_pregao") == 5, "Quinta-feira")
                   .when(F.col("dia_semana_pregao") == 6, "Sexta-feira")
                   .when(F.col("dia_semana_pregao") == 7, "Sábado"))
    
    # ETAPA 4: CRIAÇÃO DE MÉTRICAS ADICIONAIS
    logger.info("=== ETAPA 4: MÉTRICAS ADICIONAIS ===")
    
    # Criar categorias de participação
    df_final = df_with_date_calcs \
        .withColumn("categoria_participacao",
                   F.when(F.col("participation_percentage") >= 3.0, "Alta")
                   .when(F.col("participation_percentage") >= 1.0, "Média")
                   .when(F.col("participation_percentage") >= 0.1, "Baixa")
                   .otherwise("Micro")) \
        .withColumn("valor_mercado_estimado",
                   F.col("theoretical_quantity") * F.col("participation_percentage")) \
        .withColumn("data_processamento", F.current_timestamp())
    
    # ETAPA 5: PREPARAÇÃO PARA SALVAMENTO
    logger.info("=== ETAPA 5: PREPARAÇÃO DOS DADOS REFINADOS ===")
    
    # Adicionar colunas de particionamento
    df_partitioned = df_final \
        .withColumn("partition_year", F.year(F.col("data_pregao_date"))) \
        .withColumn("partition_month", F.month(F.col("data_pregao_date"))) \
        .withColumn("partition_day", F.dayofmonth(F.col("data_pregao_date"))) \
        .withColumn("ticker_group", F.substring(F.col("ticker_symbol"), 1, 4))
    
    # Converter de volta para DynamicFrame
    refined_dynamic_frame = DynamicFrame.fromDF(df_partitioned, glueContext, "refined_data")
    
    logger.info(f"Total de registros refinados: {refined_dynamic_frame.count()}")
    refined_dynamic_frame.printSchema()
    
    # ETAPA 6: SALVAMENTO DOS DADOS REFINADOS
    logger.info("=== ETAPA 6: SALVAMENTO NO S3 ===")
    
    # Caminho de destino particionado
    output_path = f"s3://{args['target_bucket']}/refined-data/bovespa/"
    
    # Salvar dados refinados particionados por data e ticker
    glueContext.write_dynamic_frame.from_options(
        frame=refined_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": output_path,
            "partitionKeys": ["partition_year", "partition_month", "partition_day", "ticker_group"]
        },
        format="parquet",
        format_options={
            "compression": "snappy"
        },
        transformation_ctx="refined_data_sink"
    )
    
    logger.info(f"Dados salvos em: {output_path}")
    
    # ETAPA 7: CATALOGAÇÃO AUTOMÁTICA NO GLUE CATALOG
    logger.info("=== ETAPA 7: CATALOGAÇÃO NO GLUE CATALOG ===")
    
    # Criar tabela no Glue Catalog
    glueContext.create_dynamic_frame.from_catalog(
        database="default",
        table_name="bovespa_refined_data",
        transformation_ctx="catalog_table"
    )
    
    # Atualizar partições no catálogo
    spark.sql(f"""
        ALTER TABLE default.bovespa_refined_data 
        ADD IF NOT EXISTS PARTITION (
            partition_year={datetime.strptime(args['processing_date'], '%Y-%m-%d').year},
            partition_month={datetime.strptime(args['processing_date'], '%Y-%m-%d').month},
            partition_day={datetime.strptime(args['processing_date'], '%Y-%m-%d').day}
        )
        LOCATION '{output_path}partition_year={datetime.strptime(args['processing_date'], '%Y-%m-%d').year}/partition_month={datetime.strptime(args['processing_date'], '%Y-%m-%d').month}/partition_day={datetime.strptime(args['processing_date'], '%Y-%m-%d').day}/'
    """)
    
    # ETAPA 8: SALVAR DADOS AGREGADOS SEPARADAMENTE
    logger.info("=== ETAPA 8: DADOS AGREGADOS ===")
    
    # Salvar dados agregados por tipo
    aggregated_dynamic_frame = DynamicFrame.fromDF(df_aggregated, glueContext, "aggregated_data")
    
    aggregated_output_path = f"s3://{args['target_bucket']}/refined-data/bovespa-aggregated/"
    
    glueContext.write_dynamic_frame.from_options(
        frame=aggregated_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": aggregated_output_path,
            "partitionKeys": ["data_pregao"]
        },
        format="parquet",
        transformation_ctx="aggregated_data_sink"
    )
    
    # ESTATÍSTICAS FINAIS
    logger.info("=== ESTATÍSTICAS FINAIS ===")
    logger.info(f"Data processada: {args['processing_date']}")
    logger.info(f"Registros processados: {df_final.count()}")
    logger.info(f"Tipos de ação únicos: {df_final.select('tipo_acao').distinct().count()}")
    logger.info(f"Tickers únicos: {df_final.select('ticker_symbol').distinct().count()}")
    
    # Mostrar amostra dos dados finais
    logger.info("Amostra dos dados finais:")
    df_final.select(
        "ticker_symbol", "company_name", "tipo_acao", 
        "theoretical_quantity", "participation_percentage",
        "categoria_participacao", "dias_desde_extracao"
    ).show(10, truncate=False)
    
    logger.info("Job Glue executado com sucesso!")
    
except Exception as e:
    logger.error(f"Erro na execução do job Glue: {str(e)}")
    raise e

finally:
    # Finalizar job
    job.commit()
    logger.info("Job Glue finalizado")
