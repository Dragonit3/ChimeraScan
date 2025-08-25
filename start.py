#!/usr/bin/env python3
"""
Script de inicialização do Sistema de Detecção de Fraudes TecBan
Configura o ambiente e inicia todos os componentes
"""
import os
import sys
import logging
from pathlib import Path

# Adicionar diretório do projeto ao Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Também adicionar ao PYTHONPATH para garantir imports absolutos
os.environ['PYTHONPATH'] = str(project_root) + os.pathsep + os.environ.get('PYTHONPATH', '')

from config.settings import settings
from data.models import create_database_engine, create_tables
from main import create_app

def setup_logging():
    """Configura sistema de logging"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('fraud_detection.log'),
            logging.StreamHandler()
        ]
    )

def setup_database():
    """Configura banco de dados"""
    try:
        engine = create_database_engine(settings.database.url)
        create_tables(engine)
        print("✅ Database configured successfully")
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def check_environment():
    """Verifica configurações do ambiente"""
    print("🔍 Checking environment configuration...")
    
    checks = [
        ("Ethereum RPC URL", settings.blockchain.ethereum_rpc_url != ""),
        ("Database URL", settings.database.url != ""),
        ("Redis URL", settings.cache.redis_url != ""),
    ]
    
    all_good = True
    for name, check in checks:
        if check:
            print(f"✅ {name}: OK")
        else:
            print(f"❌ {name}: Missing configuration")
            all_good = False
    
    return all_good

def print_banner():
    """Exibe banner do sistema"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║                🛡️  ChimeraScan System                     ║
    ║                                                          ║
    ║    Sistema de Detecção de Fraudes em Ativos Tokenizados  ║
    ║                        v1.0.0                            ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Função principal de inicialização"""
    print_banner()
    
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting ChimeraScan System initialization...")
    
    # Verificar ambiente
    if not check_environment():
        print("\n❌ Environment check failed. Please check your configuration.")
        print("📝 Copy .env.example to .env and fill in the required values.")
        sys.exit(1)
    
    # Configurar banco de dados
    if not setup_database():
        print("\n❌ Database setup failed. Please check your database configuration.")
        sys.exit(1)
    
    print("\n🚀 Starting fraud detection system...")
    print(f"🌐 Dashboard will be available at: http://localhost:5000")
    print(f"📊 API documentation at: http://localhost:5000/api/v1/")
    print(f"🔧 Debug mode: {settings.debug}")
    print(f"📈 Detection threshold: {settings.detection.anomaly_detection_threshold}")
    
    # Criar e executar aplicação
    app = create_app()
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=settings.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 System shutdown requested by user")
        logger.info("System shutdown requested")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        logger.error(f"System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
