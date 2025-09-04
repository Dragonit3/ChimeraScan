"""
Wash Trading Detection Interfaces
Define contracts for wash trading detection components
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from data.models import TransactionData

class WashTradingType(Enum):
    """Tipos de padrões de wash trading"""
    CIRCULAR = "CIRCULAR"          # A->B->C->A
    BACK_AND_FORTH = "BACK_FORTH"  # A<->B repetitive
    MULTI_HOP = "MULTI_HOP"        # A->B->C->D->A
    SELF_TRADING = "SELF_TRADING"  # A->A através de contratos

@dataclass
class WashTradingPattern:
    """Representa um padrão de wash trading detectado"""
    pattern_id: str
    pattern_type: WashTradingType
    involved_addresses: List[str]
    transaction_hashes: List[str]
    total_volume: float
    transaction_count: int
    time_span_minutes: float
    confidence_score: float
    detection_algorithm: str
    first_detected: datetime
    last_activity: datetime
    context_data: Dict[str, Any]

@dataclass
class WashTradingResult:
    """Resultado da análise de wash trading"""
    is_detected: bool
    confidence_score: float
    patterns_found: List[WashTradingPattern]
    analysis_details: Dict[str, Any]
    processing_time_ms: float
    algorithm_used: str

@dataclass
class AddressPair:
    """Relacionamento entre dois endereços"""
    address_a: str
    address_b: str
    relationship_score: float
    transaction_count: int
    total_volume: float
    avg_transaction_value: float
    first_interaction: datetime
    last_interaction: datetime
    interaction_frequency: float  # transações por hora

class IWashTradingDetector(ABC):
    """Interface principal para detecção de wash trading"""
    
    @abstractmethod
    async def analyze_transaction(self, 
                                transaction: TransactionData,
                                config: Dict[str, Any]) -> WashTradingResult:
        """
        Analisa uma transação em busca de padrões de wash trading
        
        Args:
            transaction: Transação a ser analisada
            config: Configuração da regra
            
        Returns:
            Resultado da análise com padrões detectados
        """
        pass
    
    @abstractmethod
    async def analyze_address_pair(self,
                                 address_a: str,
                                 address_b: str,
                                 time_window: timedelta) -> AddressPair:
        """
        Analisa relacionamento entre dois endereços
        
        Args:
            address_a: Primeiro endereço
            address_b: Segundo endereço  
            time_window: Janela de tempo para análise
            
        Returns:
            Dados do relacionamento entre os endereços
        """
        pass

class ITransactionGraphProvider(ABC):
    """Interface para análise de grafo de transações"""
    
    @abstractmethod
    async def get_address_relationships(self, 
                                      address: str,
                                      depth: int = 2,
                                      time_window: timedelta = timedelta(hours=24)) -> List[AddressPair]:
        """
        Obtém relacionamentos de um endereço com outros
        
        Args:
            address: Endereço para analisar
            depth: Profundidade da busca no grafo
            time_window: Janela de tempo para considerar
            
        Returns:
            Lista de relacionamentos encontrados
        """
        pass
    
    @abstractmethod
    async def find_transaction_paths(self,
                                   from_address: str,
                                   to_address: str,
                                   max_hops: int = 5,
                                   time_window: timedelta = timedelta(hours=24)) -> List[List[TransactionData]]:
        """
        Encontra caminhos de transações entre dois endereços
        
        Args:
            from_address: Endereço de origem
            to_address: Endereço de destino
            max_hops: Máximo de saltos permitidos
            time_window: Janela de tempo para busca
            
        Returns:
            Lista de caminhos encontrados (cada caminho é lista de transações)
        """
        pass

class ITemporalPatternAnalyzer(ABC):
    """Interface para análise de padrões temporais"""
    
    @abstractmethod
    async def analyze_timing_patterns(self, 
                                    transactions: List[TransactionData]) -> Dict[str, Any]:
        """
        Analisa padrões temporais em lista de transações
        
        Args:
            transactions: Lista de transações para analisar
            
        Returns:
            Métricas de padrões temporais detectados
        """
        pass
    
    @abstractmethod
    async def detect_regular_intervals(self,
                                     transactions: List[TransactionData],
                                     tolerance_seconds: int = 300) -> Dict[str, Any]:
        """
        Detecta intervalos regulares entre transações
        
        Args:
            transactions: Lista de transações
            tolerance_seconds: Tolerância para considerar intervalos regulares
            
        Returns:
            Dados sobre regularidade temporal detectada
        """
        pass

class IVolumeAnalyzer(ABC):
    """Interface para análise de volume e valores"""
    
    @abstractmethod
    async def analyze_value_similarity(self,
                                     transactions: List[TransactionData],
                                     similarity_threshold: float = 0.95) -> Dict[str, Any]:
        """
        Analisa similaridade de valores entre transações
        
        Args:
            transactions: Lista de transações
            similarity_threshold: Threshold para considerar valores similares
            
        Returns:
            Métricas de similaridade de valores
        """
        pass
    
    @abstractmethod
    async def detect_volume_preservation(self,
                                       transaction_path: List[TransactionData],
                                       preservation_threshold: float = 0.90) -> Dict[str, Any]:
        """
        Detecta preservação de volume através de um caminho de transações
        
        Args:
            transaction_path: Caminho de transações (A->B->C->A)
            preservation_threshold: Threshold para preservação de valor
            
        Returns:
            Dados sobre preservação de volume detectada
        """
        pass
