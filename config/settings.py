"""
Configurações do Sistema de Detecção de Fraudes
Seguindo princípios de Separation of Concerns e Adaptabilidade
"""
import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BlockchainConfig:
    """Configurações da blockchain"""
    ethereum_rpc_url: str = os.getenv("ETHEREUM_RPC_URL", "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY")
    etherscan_api_key: str = os.getenv("ETHERSCAN_API_KEY", "")
    block_confirmation: int = 12
    gas_price_threshold: int = 100  # Gwei

@dataclass
class DatabaseConfig:
    """Configurações do banco de dados"""
    url: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/fraud_detection")
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30

@dataclass
class CacheConfig:
    """Configurações do cache Redis"""
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    default_ttl: int = 3600  # 1 hora
    transaction_cache_ttl: int = 86400  # 24 horas

@dataclass
class AlertConfig:
    """Configurações de alertas"""
    email_smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    email_port: int = 587
    email_user: str = os.getenv("SMTP_USER", "")
    email_password: str = os.getenv("SMTP_PASSWORD", "")
    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

@dataclass
class DetectionConfig:
    """Configurações de detecção"""
    # Limites para detecção de anomalias
    high_value_threshold: float = 100000.0  # USD
    suspicious_gas_multiplier: float = 5.0
    wash_trading_time_window: int = 300  # 5 minutos
    new_wallet_age_threshold: int = 86400  # 24 horas
    
    # Fraud Detection Thresholds
    anomaly_detection_threshold: float = 0.5  # Threshold para marcar transação como suspeita
    pattern_detection_window: int = 3600  # 1 hora

class Settings:
    """Configurações centralizadas do sistema"""
    
    def __init__(self):
        self.blockchain = BlockchainConfig()
        self.database = DatabaseConfig()
        self.cache = CacheConfig()
        self.alerts = AlertConfig()
        self.detection = DetectionConfig()
        
        # Configurações gerais
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.api_rate_limit = int(os.getenv("API_RATE_LIMIT", "1000"))
        
        # Tokens suportados (ERC20/721)
        self.supported_tokens = {
            "USDC": "0xA0b86a33E6441eBCC4BA01C1E4F9D8FA19A71E6",
            "BRL1": "0x", # Token BRL hipotético
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        }
        
        # Exchanges conhecidas para monitoramento
        self.known_exchanges = [
            "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",  # Binance
            "0xD551234Ae421e3BCBA99A0Da6d736074f22192FF",  # Binance 2
            "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
        ]

# Singleton pattern para configurações
settings = Settings()
