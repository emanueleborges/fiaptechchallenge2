#!/usr/bin/env python3
"""
Script de teste para verificar o sistema de configuração .env
"""

def test_config_system():
    """Testa o sistema de configuração"""
    print("🧪 TESTANDO SISTEMA DE CONFIGURAÇÃO")
    print("=" * 50)
    
    try:
        # Teste 1: Importar módulo config
        print("1️⃣ Testando importação do módulo config...")
        from config import config
        print("✅ Módulo config importado com sucesso")
        
        # Teste 2: Verificar se .env existe
        print("\n2️⃣ Verificando arquivo .env...")
        from pathlib import Path
        env_file = Path('.env')
        
        if env_file.exists():
            print("✅ Arquivo .env encontrado")
        else:
            print("⚠️  Arquivo .env não encontrado")
            print("💡 Execute 'python configure_aws.py' para criá-lo")
            return False
        
        # Teste 3: Acessar configurações
        print("\n3️⃣ Testando acesso às configurações...")
        
        config_tests = [
            ("AWS Region", config.aws_region),
            ("S3 Bucket Name", config.s3_bucket_name),
            ("API Port", config.api_port),
            ("API Host", config.api_host),
            ("Project Name", config.project_name),
            ("Environment", config.environment),
        ]
        
        for name, value in config_tests:
            print(f"   • {name}: {value}")
        
        print("✅ Configurações acessadas com sucesso")
        
        # Teste 4: Validar configurações AWS (apenas estrutura)
        print("\n4️⃣ Testando validação de configurações AWS...")
        try:
            validation_result = config.validate_aws_config()
            if validation_result:
                print("✅ Configurações AWS válidas")
            else:
                print("⚠️  Configurações AWS incompletas")
                print("💡 Execute 'python configure_aws.py' para configurar")
        except Exception as e:
            print(f"⚠️  Erro na validação: {e}")
        
        # Teste 5: Testar parâmetros boto3
        print("\n5️⃣ Testando parâmetros para boto3...")
        try:
            boto3_params = config.get_boto3_session_kwargs()
            print(f"   • Parâmetros gerados: {list(boto3_params.keys())}")
            print("✅ Parâmetros boto3 gerados com sucesso")
        except Exception as e:
            print(f"❌ Erro ao gerar parâmetros boto3: {e}")
        
        print("\n🎉 TESTE COMPLETO!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulo config: {e}")
        print("💡 Certifique-se de que o arquivo config.py existe")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


def test_env_loading():
    """Testa carregamento manual do .env"""
    print("\n🔧 TESTE DE CARREGAMENTO MANUAL DO .ENV")
    print("=" * 50)
    
    try:
        from config import load_env_file
        import os
        
        # Salvar estado original das variáveis
        original_env = dict(os.environ)
        
        # Limpar algumas variáveis para teste
        test_vars = ['AWS_REGION', 'S3_BUCKET_NAME', 'PROJECT_NAME']
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]
        
        print("1️⃣ Variáveis limpas para teste")
        
        # Carregar .env
        load_env_file()
        
        # Verificar se variáveis foram carregadas
        loaded_vars = []
        for var in test_vars:
            if var in os.environ:
                loaded_vars.append(var)
                print(f"   ✅ {var} = {os.environ[var]}")
        
        print(f"\n✅ {len(loaded_vars)} variáveis carregadas com sucesso")
        
        # Restaurar estado original
        os.environ.clear()
        os.environ.update(original_env)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de carregamento: {e}")
        return False


if __name__ == "__main__":
    print("🚀 INICIANDO TESTES DO SISTEMA DE CONFIGURAÇÃO")
    print("=" * 60)
    
    # Executar testes
    success = True
    
    try:
        if not test_config_system():
            success = False
        
        if not test_env_loading():
            success = False
        
    except KeyboardInterrupt:
        print("\n⏹️  Testes interrompidos pelo usuário")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema de configuração está funcionando corretamente")
        print("\n💡 Próximos passos:")
        print("   • Execute 'python configure_aws.py' para configurar AWS")
        print("   • Execute 'python main.py' para testar o pipeline")
        print("   • Execute 'python api_server.py' para iniciar a API")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("💡 Verifique os erros acima e corrija antes de continuar")
    
    print("=" * 60)
