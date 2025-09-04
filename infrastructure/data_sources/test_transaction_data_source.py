"""
Test Transaction Data Source
Implementa ITransactionDataSource para ambiente de testes
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from data.models import TransactionData
from interfaces.data_sources import (
    ITransactionDataSource, TransactionRelationship, CircularPath
)
from infrastructure.factories.test_pattern_factory import TestPatternFactory, EnhancedTestPatternFactory

logger = logging.getLogger(__name__)


class TestTransactionDataSource(ITransactionDataSource):
    """
    Data source para testes que gera dados realistas baseados em padrões
    
    Implementa:
    - DIP: Implementa interface abstrata
    - SRP: Responsabilidade única - prover dados de teste
    - Strategy Pattern: Diferentes estratégias de geração
    """
    
    def __init__(self, use_enhanced_factory: bool = True):
        self.factory = EnhancedTestPatternFactory() if use_enhanced_factory else TestPatternFactory()
        
        # Cache de dados gerados para consistência
        self._transaction_cache: Dict[str, List[TransactionData]] = {}
        self._relationship_cache: Dict[tuple, List[TransactionRelationship]] = {}
        
        logger.info("TestTransactionDataSource initialized")
    
    async def get_transaction_history(self, 
                                    address: str,
                                    time_window: timedelta,
                                    max_transactions: int = 1000) -> List[TransactionData]:
        """
        Gera histórico de transações baseado no endereço
        
        Estratégia: Diferentes padrões baseados nas características do endereço
        """
        cache_key = f"{address}_{time_window.total_seconds()}"
        
        if cache_key in self._transaction_cache:
            return self._transaction_cache[cache_key]
        
        transactions = []
        
        # Estratégia baseada no padrão do endereço
        if self._is_back_forth_address(address):
            # Gerar padrão back-and-forth
            partner_address = self._generate_partner_address(address)
            transactions = await self.factory.create_sophisticated_back_forth(
                address, partner_address, {
                    "base_value": 7500.0,
                    "transaction_count": 12,
                    "time_interval_minutes": 20
                }
            )
            
        elif self._is_circular_address(address):
            # Gerar padrão circular
            circle_addresses = self._generate_circle_addresses(address)
            transactions = await self.factory.create_layered_circular_scenario(
                circle_addresses, {
                    "base_value": 12000.0,
                    "transaction_count": 15,
                    "time_interval_minutes": 25
                }
            )
            
        elif self._is_self_trading_address(address):
            # Gerar self-trading
            transactions = await self.factory.create_self_trading_scenario(
                address, {
                    "base_value": 5000.0
                }
            )
        else:
            # Gerar transações normais (para controle)
            transactions = await self._generate_normal_transactions(address, time_window)
        
        # Filtrar por time_window e limitar
        cutoff_time = datetime.utcnow() - time_window
        filtered_transactions = [
            tx for tx in transactions 
            if tx.timestamp >= cutoff_time
        ][:max_transactions]
        
        self._transaction_cache[cache_key] = filtered_transactions
        logger.info(f"Generated {len(filtered_transactions)} transactions for {address[:8]}...")
        
        return filtered_transactions
    
    async def get_address_relationships(self,
                                      address: str,
                                      time_window: timedelta,
                                      min_interactions: int = 3) -> List[TransactionRelationship]:
        """
        Gera relacionamentos baseados no histórico simulado
        """
        cache_key = (address, time_window.total_seconds(), min_interactions)
        
        if cache_key in self._relationship_cache:
            return self._relationship_cache[cache_key]
        
        relationships = []
        transactions = await self.get_transaction_history(address, time_window)
        
        if transactions:
            # Agrupar transações por endereço relacionado
            address_groups = self._group_transactions_by_counterpart(transactions, address)
            
            for counterpart_address, related_txs in address_groups.items():
                if len(related_txs) >= min_interactions:
                    relationship = self._create_relationship(
                        address, counterpart_address, related_txs, time_window
                    )
                    relationships.append(relationship)
        
        # Ordenar por score de relacionamento
        relationships.sort(key=lambda r: r.relationship_score, reverse=True)
        
        self._relationship_cache[cache_key] = relationships
        logger.info(f"Generated {len(relationships)} relationships for {address[:8]}...")
        
        return relationships
    
    async def find_circular_paths(self,
                                starting_address: str,
                                max_hops: int = 5,
                                time_window: timedelta = timedelta(hours=24)) -> List[CircularPath]:
        """
        Encontra caminhos circulares nos dados gerados
        """
        if not self._is_circular_address(starting_address):
            return []  # Apenas endereços circulares têm caminhos
        
        # Gerar dados circulares
        circle_addresses = self._generate_circle_addresses(starting_address)
        transactions = await self.factory.create_circular_scenario(
            circle_addresses, {
                "base_value": 15000.0,
                "transaction_count": 12,
                "time_interval_minutes": 30
            }
        )
        
        # Detectar caminhos circulares nos dados
        circular_paths = []
        
        # Simular detecção de ciclo
        if len(transactions) >= 3:
            # Agrupar transações em ciclos
            cycle_size = len(circle_addresses)
            cycles = len(transactions) // cycle_size
            
            for cycle_start in range(0, cycles * cycle_size, cycle_size):
                cycle_transactions = transactions[cycle_start:cycle_start + cycle_size]
                
                if len(cycle_transactions) == cycle_size:
                    # Verificar se forma ciclo completo
                    first_from = cycle_transactions[0].from_address
                    last_to = cycle_transactions[-1].to_address
                    
                    if first_from.lower() == last_to.lower():
                        total_volume = sum(tx.value for tx in cycle_transactions)
                        initial_volume = cycle_transactions[0].value
                        preservation_ratio = cycle_transactions[-1].value / initial_volume if initial_volume > 0 else 0
                        
                        time_span = cycle_transactions[-1].timestamp - cycle_transactions[0].timestamp
                        
                        circular_path = CircularPath(
                            path_transactions=cycle_transactions,
                            involved_addresses=list(set([tx.from_address for tx in cycle_transactions] + 
                                                      [tx.to_address for tx in cycle_transactions])),
                            total_volume=total_volume,
                            volume_preservation_ratio=preservation_ratio,
                            time_span=time_span,
                            hop_count=len(cycle_transactions),
                            cycle_complete=True
                        )
                        circular_paths.append(circular_path)
        
        logger.info(f"Found {len(circular_paths)} circular paths for {starting_address[:8]}...")
        return circular_paths
    
    def _is_back_forth_address(self, address: str) -> bool:
        """Identifica se endereço deve simular back-and-forth"""
        return "AAAABBBB" in address.upper() or "FFFFEEEE" in address.upper()
    
    def _is_circular_address(self, address: str) -> bool:
        """Identifica se endereço deve simular padrão circular"""
        # Padrões que indicam cenário circular
        circular_patterns = [
            "11110000",  # Original
            "55550000",  # Original  
            "11112222",  # Novo padrão do teste
            "00009999",  # Padrão reverso
            "1111222233334444",  # Padrão completo do teste
        ]
        
        address_upper = address.upper()
        for pattern in circular_patterns:
            if pattern.upper() in address_upper:
                return True
        
        return False
    
    def _is_self_trading_address(self, address: str) -> bool:
        """Identifica se endereço deve simular self-trading"""
        return len(set(address.lower())) <= 3  # Endereço com poucos caracteres únicos
    
    def _generate_partner_address(self, address: str) -> str:
        """Gera endereço parceiro para back-and-forth"""
        if "AAAABBBB" in address.upper():
            return "0xFFFFEEEEDDDDCCCCBBBBAAAA3333222211110000"
        return "0xAAAABBBBCCCCDDDDEEEEFFFF0000111122223333"
    
    def _generate_circle_addresses(self, starting_address: str) -> List[str]:
        """Gera lista de endereços para formar círculo"""
        base_addresses = [
            starting_address,
            "0x2222000033330000444400005555000066660000",
            "0x3333000044440000555500006666000077770000",
            "0x4444000055550000666600007777000088880000"
        ]
        return base_addresses[:4]  # Círculo de 4 endereços
    
    async def _generate_normal_transactions(self, address: str, time_window: timedelta) -> List[TransactionData]:
        """Gera transações normais para endereços de controle"""
        return await self.factory.create_self_trading_scenario(address, {"base_value": 100.0})
    
    def _group_transactions_by_counterpart(self, transactions: List[TransactionData], 
                                         main_address: str) -> Dict[str, List[TransactionData]]:
        """Agrupa transações por endereço contraparte"""
        groups = {}
        
        for tx in transactions:
            counterpart = None
            if tx.from_address.lower() == main_address.lower():
                counterpart = tx.to_address
            elif tx.to_address and tx.to_address.lower() == main_address.lower():
                counterpart = tx.from_address
            
            if counterpart:
                if counterpart not in groups:
                    groups[counterpart] = []
                groups[counterpart].append(tx)
        
        return groups
    
    def _create_relationship(self, address_a: str, address_b: str, 
                           transactions: List[TransactionData], 
                           time_window: timedelta) -> TransactionRelationship:
        """Cria objeto de relacionamento a partir de transações"""
        total_volume = sum(tx.value for tx in transactions)
        interaction_frequency = len(transactions) / time_window.total_seconds() * 3600  # por hora
        
        # Score baseado em frequência e volume
        relationship_score = min(1.0, interaction_frequency / 10.0 + (total_volume / 100000.0))
        
        # Padrão de indicadores baseado no tipo de relacionamento
        pattern_indicators = {
            "alternating_pattern": self._detect_alternating_pattern(transactions, address_a, address_b),
            "volume_similarity": self._calculate_volume_similarity(transactions),
            "timing_regularity": self._calculate_timing_regularity(transactions),
            "suspicious_score": relationship_score * len(transactions) / 10.0
        }
        
        return TransactionRelationship(
            address_a=address_a,
            address_b=address_b,
            transactions=transactions,
            total_volume=total_volume,
            interaction_frequency=interaction_frequency,
            relationship_score=relationship_score,
            first_interaction=min(tx.timestamp for tx in transactions),
            last_interaction=max(tx.timestamp for tx in transactions),
            pattern_indicators=pattern_indicators
        )
    
    def _detect_alternating_pattern(self, transactions: List[TransactionData], 
                                  address_a: str, address_b: str) -> float:
        """Detecta padrão alternado A→B, B→A"""
        if len(transactions) < 4:
            return 0.0
        
        sorted_txs = sorted(transactions, key=lambda tx: tx.timestamp)
        alternations = 0
        
        for i in range(1, len(sorted_txs)):
            prev_tx = sorted_txs[i-1]
            curr_tx = sorted_txs[i]
            
            # Verificar se houve alternação de direção
            prev_direction = self._get_direction(prev_tx, address_a, address_b)
            curr_direction = self._get_direction(curr_tx, address_a, address_b)
            
            if prev_direction != curr_direction and prev_direction is not None and curr_direction is not None:
                alternations += 1
        
        return alternations / (len(sorted_txs) - 1) if len(sorted_txs) > 1 else 0.0
    
    def _get_direction(self, tx: TransactionData, address_a: str, address_b: str) -> Optional[str]:
        """Determina direção da transação"""
        if tx.from_address.lower() == address_a.lower() and tx.to_address and tx.to_address.lower() == address_b.lower():
            return "A→B"
        elif tx.from_address.lower() == address_b.lower() and tx.to_address and tx.to_address.lower() == address_a.lower():
            return "B→A"
        return None
    
    def _calculate_volume_similarity(self, transactions: List[TransactionData]) -> float:
        """Calcula similaridade de volume"""
        if len(transactions) < 2:
            return 0.0
        
        values = [tx.value for tx in transactions]
        mean_value = sum(values) / len(values)
        variance = sum((v - mean_value) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        coefficient_of_variation = std_dev / mean_value if mean_value > 0 else 1.0
        similarity = max(0.0, 1.0 - coefficient_of_variation)
        
        return similarity
    
    def _calculate_timing_regularity(self, transactions: List[TransactionData]) -> float:
        """Calcula regularidade temporal"""
        if len(transactions) < 3:
            return 0.0
        
        sorted_txs = sorted(transactions, key=lambda tx: tx.timestamp)
        intervals = []
        
        for i in range(1, len(sorted_txs)):
            interval = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return 0.0
        
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((interval - mean_interval) ** 2 for interval in intervals) / len(intervals)
        std_dev = variance ** 0.5
        
        regularity = 1.0 - min(1.0, std_dev / mean_interval if mean_interval > 0 else 1.0)
        return regularity
