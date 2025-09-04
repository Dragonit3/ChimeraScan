"""
Data Source Abstraction for Wash Trading Detection
Implementa DIP (Dependency Inversion Principle) para fontes de dados
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from data.models import TransactionData


@dataclass
class TransactionRelationship:
    """Representa relacionamento entre dois endereços com dados históricos"""
    address_a: str
    address_b: str
    transactions: List[TransactionData]
    total_volume: float
    interaction_frequency: float
    relationship_score: float
    first_interaction: datetime
    last_interaction: datetime
    pattern_indicators: Dict[str, Any]


@dataclass 
class CircularPath:
    """Representa um caminho circular de transações"""
    path_transactions: List[TransactionData]
    involved_addresses: List[str]
    total_volume: float
    volume_preservation_ratio: float
    time_span: timedelta
    hop_count: int
    cycle_complete: bool


class ITransactionDataSource(ABC):
    """
    Interface abstrata para fontes de dados de transações
    
    Implementa DIP: Classes de alto nível não dependem de implementações concretas
    """
    
    @abstractmethod
    async def get_transaction_history(self, 
                                    address: str,
                                    time_window: timedelta,
                                    max_transactions: int = 1000) -> List[TransactionData]:
        """Obter histórico de transações para um endereço"""
        pass
    
    @abstractmethod
    async def get_address_relationships(self,
                                      address: str,
                                      time_window: timedelta,
                                      min_interactions: int = 3) -> List[TransactionRelationship]:
        """Obter relacionamentos entre endereços com dados históricos"""
        pass
    
    @abstractmethod
    async def find_circular_paths(self,
                                starting_address: str,
                                max_hops: int = 5,
                                time_window: timedelta = timedelta(hours=24)) -> List[CircularPath]:
        """Encontrar caminhos circulares partindo de um endereço"""
        pass


class ITransactionPatternFactory(ABC):
    """
    Factory abstrata para criação de padrões de teste
    
    Implementa Factory Pattern + Strategy Pattern
    """
    
    @abstractmethod
    async def create_back_forth_scenario(self,
                                       address_a: str,
                                       address_b: str,
                                       pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """Criar cenário de back-and-forth para testes"""
        pass
    
    @abstractmethod
    async def create_circular_scenario(self,
                                     addresses: List[str],
                                     pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """Criar cenário circular para testes"""
        pass
    
    @abstractmethod
    async def create_self_trading_scenario(self,
                                         address: str,
                                         pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """Criar cenário de self-trading"""
        pass
