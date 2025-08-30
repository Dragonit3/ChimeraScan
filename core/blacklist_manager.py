"""
ChimeraScan - Módulo de Blacklist com Banco de Dados
Gerencia lista negra de endereços usando SQLite
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SeverityLevel(Enum):
    """Níveis de severidade para blacklist"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AddressType(Enum):
    """Tipos de endereço"""
    WALLET = "WALLET"
    CONTRACT = "CONTRACT"
    EXCHANGE = "EXCHANGE"
    MIXER = "MIXER"
    OTHER = "OTHER"

@dataclass
class BlacklistEntry:
    """Entrada da blacklist"""
    id: Optional[int]
    address: str
    address_type: AddressType
    severity_level: SeverityLevel
    reason: Optional[str]
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    notes: Optional[str]

class BlacklistDatabase:
    """
    Gerenciador de blacklist com banco de dados SQLite
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Inicializa conexão com banco de dados
        
        Args:
            database_url: URL do banco (ex: sqlite:///blocklist.db)
        """
        self.database_url = database_url or os.getenv('DATABASE_BLOCK_URL', 'sqlite:///blocklist.db')
        self.db_path = self._extract_db_path(self.database_url)
        self._ensure_database_exists()
        logger.info(f"BlacklistDatabase initialized with: {self.db_path}")
    
    def _extract_db_path(self, database_url: str) -> str:
        """Extrai caminho do banco da URL"""
        if database_url.startswith('sqlite:///'):
            return database_url.replace('sqlite:///', '')
        elif database_url.startswith('sqlite://'):
            return database_url.replace('sqlite://', '')
        else:
            # Assume que é um caminho direto
            return database_url
    
    def _ensure_database_exists(self):
        """Garante que o banco e tabelas existem"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
                self._create_triggers(conn)
            logger.info("Database schema verified/created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Cria tabelas necessárias"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                address_type TEXT NOT NULL,
                severity_level TEXT NOT NULL DEFAULT 'HIGH',
                reason TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT
            )
        """)
        conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Cria índices para performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_address_lookup ON blacklisted_addresses(address, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_severity ON blacklisted_addresses(severity_level)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON blacklisted_addresses(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_address_type ON blacklisted_addresses(address_type)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        conn.commit()
    
    def _create_triggers(self, conn: sqlite3.Connection):
        """Cria triggers para manutenção automática"""
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_blacklist_timestamp 
                AFTER UPDATE ON blacklisted_addresses
            BEGIN
                UPDATE blacklisted_addresses 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        conn.commit()
    
    async def is_address_blacklisted(self, address: str) -> bool:
        """
        Verifica se um endereço está na blacklist
        
        Args:
            address: Endereço Ethereum para verificar
            
        Returns:
            True se estiver blacklistado e ativo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 1 FROM blacklisted_addresses 
                    WHERE LOWER(address) = LOWER(?) 
                    AND is_active = TRUE
                """, (address,))
                
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            logger.error(f"Error checking blacklist for {address}: {e}")
            return False
    
    async def get_blacklist_info(self, address: str) -> Optional[BlacklistEntry]:
        """
        Obtém informações completas de um endereço blacklistado
        
        Args:
            address: Endereço para consultar
            
        Returns:
            BlacklistEntry se encontrado, None caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM blacklisted_addresses 
                    WHERE LOWER(address) = LOWER(?) 
                    AND is_active = TRUE
                """, (address,))
                
                row = cursor.fetchone()
                if row:
                    return BlacklistEntry(
                        id=row['id'],
                        address=row['address'],
                        address_type=AddressType(row['address_type']),
                        severity_level=SeverityLevel(row['severity_level']),
                        reason=row['reason'],
                        source=row['source'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at']),
                        is_active=bool(row['is_active']),
                        notes=row['notes']
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting blacklist info for {address}: {e}")
            return None
    
    async def add_address(self, 
                         address: str,
                         address_type: AddressType,
                         severity_level: SeverityLevel,
                         reason: Optional[str] = None,
                         source: Optional[str] = None,
                         notes: Optional[str] = None) -> bool:
        """
        Adiciona um endereço à blacklist
        
        Args:
            address: Endereço Ethereum
            address_type: Tipo do endereço
            severity_level: Nível de severidade
            reason: Motivo da inclusão
            source: Fonte da informação
            notes: Observações adicionais
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO blacklisted_addresses 
                    (address, address_type, severity_level, reason, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (address, address_type.value, severity_level.value, reason, source, notes))
                
                conn.commit()
                logger.info(f"Address {address} added to blacklist with severity {severity_level.value}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding address {address} to blacklist: {e}")
            return False
    
    async def remove_address(self, address: str, soft_delete: bool = True) -> bool:
        """
        Remove um endereço da blacklist
        
        Args:
            address: Endereço para remover
            soft_delete: Se True, marca como inativo; se False, deleta permanentemente
            
        Returns:
            True se removido com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if soft_delete:
                    conn.execute("""
                        UPDATE blacklisted_addresses 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE LOWER(address) = LOWER(?)
                    """, (address,))
                else:
                    conn.execute("""
                        DELETE FROM blacklisted_addresses 
                        WHERE LOWER(address) = LOWER(?)
                    """, (address,))
                
                conn.commit()
                action = "deactivated" if soft_delete else "deleted"
                logger.info(f"Address {address} {action} from blacklist")
                return True
                
        except Exception as e:
            logger.error(f"Error removing address {address} from blacklist: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas da blacklist
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active,
                        COUNT(CASE WHEN severity_level = 'CRITICAL' AND is_active = 1 THEN 1 END) as critical,
                        COUNT(CASE WHEN severity_level = 'HIGH' AND is_active = 1 THEN 1 END) as high,
                        COUNT(CASE WHEN severity_level = 'MEDIUM' AND is_active = 1 THEN 1 END) as medium,
                        COUNT(CASE WHEN severity_level = 'LOW' AND is_active = 1 THEN 1 END) as low
                    FROM blacklisted_addresses
                """)
                
                row = cursor.fetchone()
                return {
                    'total_entries': row[0],
                    'active_entries': row[1],
                    'by_severity': {
                        'critical': row[2],
                        'high': row[3],
                        'medium': row[4],
                        'low': row[5]
                    },
                    'database_path': self.db_path
                }
                
        except Exception as e:
            logger.error(f"Error getting blacklist statistics: {e}")
            return {}
    
    async def initialize_default_data(self) -> bool:
        """
        Inicializa dados padrão na blacklist (para desenvolvimento/demo)
        
        Returns:
            True se inicializado com sucesso
        """
        default_entries = [
            # Phishing Wallets
            ("0x1234567890abcdef1234567890abcdef12345678", AddressType.WALLET, SeverityLevel.CRITICAL, 
             "Known phishing wallet", "Chainalysis", "Multiple confirmed victims"),
            ("0xabcdef1234567890abcdef1234567890abcdef12", AddressType.WALLET, SeverityLevel.HIGH, 
             "Suspected phishing", "Community Report", "Pattern analysis match"),
            
            # Ransomware Addresses
            ("0xd4648f90A20f5bbBFFEEb0d6E7C62C9396174F2b", AddressType.WALLET, SeverityLevel.CRITICAL, 
             "Ransomware payment address", "FBI Cyber Division", "Multiple ransomware campaigns"),
            ("0xdAFC4ab80F48FdE24591aA4412a9d924EaDc0a58", AddressType.WALLET, SeverityLevel.CRITICAL, 
             "Ransomware operator", "Europol", "Confirmed criminal activity"),
            
            # Mixer Services
            ("0x42C529af2f7c1FE094501a9986E6723733154b82", AddressType.CONTRACT, SeverityLevel.HIGH, 
             "Unauthorized mixer service", "FATF Guidelines", "AML compliance violation"),
            ("0xcfAf9660251648a3723f21172e2A4D1257b2b372", AddressType.CONTRACT, SeverityLevel.MEDIUM, 
             "Privacy service", "Regulatory Watch", "Under investigation"),
            
            # Suspicious Exchanges
            ("0x7751C71663A22CF8375eA1d259640bbc46db63a7", AddressType.EXCHANGE, SeverityLevel.HIGH, 
             "Unregulated exchange", "Financial Authority", "No proper licensing"),
            ("0xDe87b67Cc523270F896Fa9C7c3B21e287101567d", AddressType.EXCHANGE, SeverityLevel.MEDIUM, 
             "High-risk exchange", "Risk Assessment", "Unusual transaction patterns"),
            
            # Test Addresses
            ("0x00d9fE085D99B33Ab2AAE8063180c63E23bF2E69", AddressType.WALLET, SeverityLevel.LOW, 
             "ChimeraScan test address", "Internal", "Used for system testing"),
            ("0x455bF23eA7575A537b6374953FA71B5F3653272c", AddressType.WALLET, SeverityLevel.MEDIUM, 
             "Demo suspicious wallet", "Internal", "Demonstration purposes")
        ]
        
        success_count = 0
        for entry in default_entries:
            if await self.add_address(*entry):
                success_count += 1
        
        logger.info(f"Initialized {success_count}/{len(default_entries)} default blacklist entries")
        return success_count == len(default_entries)

# Instância global da blacklist (singleton pattern)
_blacklist_db = None

def get_blacklist_database() -> BlacklistDatabase:
    """
    Obtém instância singleton da blacklist database
    
    Returns:
        Instância de BlacklistDatabase
    """
    global _blacklist_db
    if _blacklist_db is None:
        _blacklist_db = BlacklistDatabase()
    return _blacklist_db
