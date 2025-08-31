"""
Simple Transaction History Provider
Implementação básica para começar, sem dependências externas complexas
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from interfaces.data_providers import ITransactionHistoryProvider
from data.models import TransactionData

logger = logging.getLogger(__name__)


class SimpleTransactionHistoryProvider(ITransactionHistoryProvider):
    """
    Implementação simples de histórico de transações
    
    Responsabilidade: Fornecer dados históricos básicos para análise de padrões
    Princípios: Interface Segregation, Dependency Inversion
    
    Nota: Esta é uma implementação inicial que pode ser expandida para usar
    APIs reais (Etherscan, Infura, etc.) sem quebrar o contrato
    """
    
    def __init__(self):
        """Initialize simple provider with in-memory storage"""
        self._transaction_cache = {}  # address -> List[TransactionData]
        self._cache_expiry = {}  # address -> datetime
        self._cache_duration = timedelta(minutes=5)  # Cache por 5 minutos
        
    async def get_recent_transactions(self, 
                                    address: str, 
                                    time_window_minutes: int,
                                    limit: int = 100) -> List[TransactionData]:
        """
        Retorna transações recentes simuladas para um endereço
        
        Implementação inicial: simula algumas transações para teste
        Futura: consultará APIs reais de blockchain
        """
        try:
            # Verificar cache primeiro
            if self._is_cache_valid(address):
                cached_transactions = self._transaction_cache[address]
                return self._filter_by_time_window(cached_transactions, time_window_minutes)[:limit]
            
            # Simular algumas transações para o endereço
            simulated_transactions = self._simulate_transactions_for_address(
                address, time_window_minutes, limit
            )
            
            # Cache results
            self._transaction_cache[address] = simulated_transactions
            self._cache_expiry[address] = datetime.utcnow() + self._cache_duration
            
            return simulated_transactions
            
        except Exception as e:
            logger.warning(f"Error getting recent transactions for {address}: {e}")
            return []
    
    async def get_address_interactions(self, 
                                     from_address: str, 
                                     to_address: Optional[str],
                                     time_window_minutes: int) -> List[TransactionData]:
        """
        Retorna interações entre endereços específicos
        
        Implementação inicial: simula interações básicas
        """
        try:
            # Para estruturação, focamos em transações FROM o endereço
            from_transactions = await self.get_recent_transactions(
                from_address, time_window_minutes, 50
            )
            
            # Se to_address especificado, filtrar apenas essas interações
            if to_address:
                interactions = [
                    tx for tx in from_transactions 
                    if tx.to_address and tx.to_address.lower() == to_address.lower()
                ]
                return interactions
            
            return from_transactions
            
        except Exception as e:
            logger.warning(f"Error getting interactions for {from_address} -> {to_address}: {e}")
            return []
    
    async def get_transactions_by_value_range(self,
                                            address: str,
                                            min_value: float,
                                            max_value: float,
                                            time_window_minutes: int) -> List[TransactionData]:
        """
        Retorna transações dentro de uma faixa de valores
        
        Crucial para análise de estruturação
        """
        try:
            # Buscar todas transações recentes
            all_transactions = await self.get_recent_transactions(
                address, time_window_minutes, 200
            )
            
            # Filtrar por faixa de valores
            filtered_transactions = [
                tx for tx in all_transactions
                if min_value <= tx.value <= max_value
            ]
            
            logger.debug(f"Found {len(filtered_transactions)} transactions in range ${min_value}-${max_value} for {address[:10]}...")
            return filtered_transactions
            
        except Exception as e:
            logger.warning(f"Error getting transactions by value range for {address}: {e}")
            return []
    
    def _is_cache_valid(self, address: str) -> bool:
        """Verifica se cache ainda é válido"""
        if address not in self._cache_expiry:
            return False
        return datetime.utcnow() < self._cache_expiry[address]
    
    def _filter_by_time_window(self, 
                              transactions: List[TransactionData],
                              time_window_minutes: int) -> List[TransactionData]:
        """Filtra transações pela janela temporal"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return [
            tx for tx in transactions
            if tx.timestamp >= cutoff_time
        ]
    
    def _simulate_transactions_for_address(self,
                                         address: str,
                                         time_window_minutes: int,
                                         limit: int) -> List[TransactionData]:
        """
        Simula transações para teste da regra de estruturação
        
        Nota: Em produção, seria substituído por consultas reais à blockchain
        """
        import random
        from data.models import TransactionType
        
        transactions = []
        base_time = datetime.utcnow()
        
        # Simular padrão de possível estruturação para alguns endereços específicos
        if self._should_simulate_structuring_pattern(address):
            # Simular múltiplas transações pequenas
            num_transactions = random.randint(8, 15)  # Enough for pattern
            
            for i in range(num_transactions):
                # Valores consistentemente abaixo do threshold (9999)
                value = random.uniform(5000, 9500)  # Suspeito: próximo ao limite
                
                # Timestamps espaçados regularmente (suspeito)
                minutes_ago = random.randint(1, time_window_minutes - 1)
                tx_time = base_time - timedelta(minutes=minutes_ago)
                
                tx = TransactionData(
                    hash=f"0x{random.randint(100000000000, 999999999999):012x}structuring{i}",
                    from_address=address,
                    to_address=f"0x{random.randint(100000000000, 999999999999):012x}",
                    value=value,
                    gas_price=random.uniform(20, 40),
                    timestamp=tx_time,
                    block_number=random.randint(18000000, 18999999),
                    transaction_type=TransactionType.TRANSFER
                )
                transactions.append(tx)
        else:
            # Transações normais (não suspeitas)
            num_transactions = random.randint(1, 5)
            
            for i in range(num_transactions):
                # Valores variados, alguns acima do threshold
                value = random.uniform(500, 50000)  
                
                minutes_ago = random.randint(1, time_window_minutes - 1)
                tx_time = base_time - timedelta(minutes=minutes_ago)
                
                tx = TransactionData(
                    hash=f"0x{random.randint(100000000000, 999999999999):012x}normal{i}",
                    from_address=address,
                    to_address=f"0x{random.randint(100000000000, 999999999999):012x}",
                    value=value,
                    gas_price=random.uniform(20, 40),
                    timestamp=tx_time,
                    block_number=random.randint(18000000, 18999999),
                    transaction_type=TransactionType.TRANSFER
                )
                transactions.append(tx)
        
        return sorted(transactions, key=lambda tx: tx.timestamp, reverse=True)[:limit]
    
    def _should_simulate_structuring_pattern(self, address: str) -> bool:
        """
        Determina se deve simular padrão de estruturação para teste
        
        Endereços específicos terão padrão suspeito para teste da regra
        """
        # Endereços que terão padrão de estruturação simulado
        structuring_test_addresses = [
            "0xstructuring1234567890abcdef1234567890abcdef",
            "0xsmurfing1234567890abcdef1234567890abcdef123",
            "0xevasion1234567890abcdef1234567890abcdef1234"
        ]
        
        return address.lower() in [addr.lower() for addr in structuring_test_addresses]
