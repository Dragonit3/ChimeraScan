"""
Modelos de dados para o sistema de detecção de fraudes
Seguindo princípios de Manutenibilidade e Separation of Concerns
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid

Base = declarative_base()

class RiskLevel(Enum):
    """Níveis de risco"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(Enum):
    """Status do alerta"""
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

class TransactionType(Enum):
    """Tipos de transação"""
    TRANSFER = "TRANSFER"
    SWAP = "SWAP"
    MINT = "MINT"
    BURN = "BURN"
    APPROVAL = "APPROVAL"
    CONTRACT_INTERACTION = "CONTRACT_INTERACTION"

# SQLAlchemy Models
class Transaction(Base):
    """Modelo para transações blockchain"""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hash = Column(String(66), unique=True, nullable=False, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    block_hash = Column(String(66), nullable=False)
    transaction_index = Column(Integer, nullable=False)
    
    # Dados da transação
    from_address = Column(String(42), nullable=False, index=True)
    to_address = Column(String(42), nullable=True, index=True)
    value = Column(Float, nullable=False)
    gas = Column(Integer, nullable=False)
    gas_price = Column(Float, nullable=False)
    gas_used = Column(Integer, nullable=True)
    
    # Metadados
    timestamp = Column(DateTime, nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False)
    token_address = Column(String(42), nullable=True, index=True)
    token_amount = Column(Float, nullable=True)
    
    # Análise de risco
    risk_score = Column(Float, nullable=True, index=True)
    risk_level = Column(String(20), nullable=True, index=True)
    is_suspicious = Column(Boolean, default=False, index=True)
    
    # Dados adicionais
    input_data = Column(Text, nullable=True)
    logs = Column(JSON, nullable=True)
    internal_transactions = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Wallet(Base):
    """Modelo para carteiras"""
    __tablename__ = "wallets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String(42), unique=True, nullable=False, index=True)
    
    # Metadados da carteira
    first_seen = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=True, index=True)
    transaction_count = Column(Integer, default=0)
    total_value_transacted = Column(Float, default=0.0)
    
    # Classificação
    is_exchange = Column(Boolean, default=False, index=True)
    is_contract = Column(Boolean, default=False, index=True)
    is_blacklisted = Column(Boolean, default=False, index=True)
    reputation_score = Column(Float, nullable=True)
    
    # Tags e labels
    tags = Column(JSON, nullable=True)
    labels = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Alert(Base):
    """Modelo para alertas de fraude"""
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Referências
    transaction_hash = Column(String(66), nullable=False, index=True)
    wallet_address = Column(String(42), nullable=True, index=True)
    
    # Dados do alerta
    rule_name = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    
    # Descrição e contexto
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    context_data = Column(JSON, nullable=True)
    
    # Status e resolução
    status = Column(String(20), default="PENDING", index=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RiskProfile(Base):
    """Perfil de risco para carteiras"""
    __tablename__ = "risk_profiles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_address = Column(String(42), nullable=False, index=True)
    
    # Scores de risco
    overall_risk_score = Column(Float, nullable=False, index=True)
    behavioral_score = Column(Float, nullable=True)
    network_score = Column(Float, nullable=True)
    temporal_score = Column(Float, nullable=True)
    
    # Padrões detectados
    detected_patterns = Column(JSON, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    
    # Histórico
    evaluation_date = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String(20), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Dataclasses para business logic
@dataclass
class TransactionData:
    """Classe para dados de transação em memória"""
    hash: str
    from_address: str
    to_address: Optional[str]
    value: float
    gas_price: float
    timestamp: datetime
    block_number: int
    transaction_type: TransactionType
    token_address: Optional[str] = None
    token_amount: Optional[float] = None
    risk_score: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlertData:
    """Classe para dados de alerta"""
    rule_name: str
    severity: RiskLevel
    transaction_hash: str
    title: str
    description: str
    risk_score: float
    wallet_address: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class WalletProfile:
    """Perfil de carteira para análise"""
    address: str
    age_hours: float
    transaction_count: int
    total_value: float
    is_exchange: bool = False
    is_contract: bool = False
    is_blacklisted: bool = False
    reputation_score: Optional[float] = None
    recent_activity: List[TransactionData] = field(default_factory=list)

# Funções utilitárias
def create_database_engine(database_url: str):
    """Cria engine do banco de dados"""
    engine = create_engine(
        database_url,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,
        pool_pre_ping=True
    )
    return engine

def create_tables(engine):
    """Cria todas as tabelas"""
    Base.metadata.create_all(engine)

def get_session_factory(engine):
    """Retorna factory de sessões"""
    return sessionmaker(bind=engine)
