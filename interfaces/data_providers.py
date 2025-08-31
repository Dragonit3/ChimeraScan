"""
Data Providers Interfaces for ChimeraScan
Defines contracts for external data access following DIP principle
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

from data.models import TransactionData


class ITransactionHistoryProvider(ABC):
    """
    Interface para provedores de histórico de transações
    
    Responsabilidade: Abstração para acesso a dados históricos
    Princípio: Interface Segregation - específica para transactions
    """
    
    @abstractmethod
    async def get_recent_transactions(self, 
                                    address: str, 
                                    time_window_minutes: int,
                                    limit: int = 100) -> List[TransactionData]:
        """
        Retorna transações recentes de um endereço
        
        Args:
            address: Endereço Ethereum
            time_window_minutes: Janela temporal em minutos
            limit: Máximo de transações a retornar
            
        Returns:
            Lista de transações dentro da janela temporal
        """
        pass
    
    @abstractmethod
    async def get_address_interactions(self, 
                                     from_address: str, 
                                     to_address: Optional[str],
                                     time_window_minutes: int) -> List[TransactionData]:
        """
        Retorna histórico de interações entre endereços
        
        Args:
            from_address: Endereço de origem
            to_address: Endereço de destino (opcional)
            time_window_minutes: Janela temporal
            
        Returns:
            Lista de transações entre os endereços
        """
        pass
    
    @abstractmethod
    async def get_transactions_by_value_range(self,
                                            address: str,
                                            min_value: float,
                                            max_value: float,
                                            time_window_minutes: int) -> List[TransactionData]:
        """
        Retorna transações dentro de uma faixa de valores
        
        Args:
            address: Endereço para buscar
            min_value: Valor mínimo USD
            max_value: Valor máximo USD  
            time_window_minutes: Janela temporal
            
        Returns:
            Lista de transações na faixa de valores
        """
        pass


class IMarketDataProvider(ABC):
    """
    Interface para provedores de dados de mercado
    
    Responsabilidade: Abstração para dados de mercado/preços
    Princípio: Interface Segregation - específica para market data
    """
    
    @abstractmethod
    async def get_token_price_deviation(self, token_address: str, timeframe_minutes: int = 60) -> float:
        """
        Retorna desvio de preço em relação à média
        
        Args:
            token_address: Endereço do token
            timeframe_minutes: Período para análise
            
        Returns:
            Desvio percentual (0.0 a 1.0)
        """
        pass
    
    @abstractmethod
    async def get_volume_spike_factor(self, token_address: str, timeframe_minutes: int = 60) -> float:
        """
        Retorna fator de spike de volume (1.0 = normal)
        
        Args:
            token_address: Endereço do token
            timeframe_minutes: Período para análise
            
        Returns:
            Multiplicador de volume (1.0+ = spike)
        """
        pass
