"""
Test Scenario Factory for Wash Trading Patterns
Implementa Factory + Strategy Pattern para criação de cenários de teste
"""
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass

from data.models import TransactionData, TransactionType
from interfaces.data_sources import ITransactionPatternFactory
import logging

logger = logging.getLogger(__name__)


@dataclass
class PatternConfig:
    """Configuração para geração de padrões"""
    base_value: float = 1000.0
    value_variation: float = 0.1  # 10% de variação
    time_interval_minutes: int = 15
    time_variation_minutes: int = 5
    transaction_count: int = 8
    gas_price_base: float = 40.0


class TestPatternFactory(ITransactionPatternFactory):
    """
    Factory concreto para criação de padrões de teste
    
    Implementa:
    - Factory Pattern: Criação centralizada
    - Strategy Pattern: Diferentes estratégias por tipo
    - SRP: Uma responsabilidade - criar padrões
    """
    
    def __init__(self):
        self.pattern_id = 0
        logger.info("TestPatternFactory initialized")
    
    async def create_back_forth_scenario(self,
                                       address_a: str,
                                       address_b: str,
                                       pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """
        Cria cenário realista de back-and-forth
        
        Padrão: A→B, B→A, A→B, B→A, etc.
        """
        config = PatternConfig(**pattern_config)
        transactions = []
        
        base_time = datetime.utcnow() - timedelta(hours=2)
        
        for i in range(config.transaction_count):
            # Alternar direção
            if i % 2 == 0:
                from_addr, to_addr = address_a, address_b
                direction = "A→B"
            else:
                from_addr, to_addr = address_b, address_a
                direction = "B→A"
            
            # Variação no valor (indicativo de wash trading)
            value_variation = random.uniform(1 - config.value_variation, 1 + config.value_variation)
            transaction_value = config.base_value * value_variation
            
            # Variação no tempo (mas mantendo padrão)
            time_offset = i * config.time_interval_minutes + random.randint(
                -config.time_variation_minutes, config.time_variation_minutes
            )
            timestamp = base_time + timedelta(minutes=time_offset)
            
            transaction = TransactionData(
                hash=f"0xbackforth{self.pattern_id:03d}_{i:03d}_{uuid.uuid4().hex[:8]}",
                from_address=from_addr,
                to_address=to_addr,
                value=transaction_value,
                gas_price=config.gas_price_base + random.uniform(-5, 5),
                timestamp=timestamp,
                block_number=18000000 + i * 100,
                transaction_type=TransactionType.TRANSFER
            )
            
            transactions.append(transaction)
            logger.debug(f"Created back-forth tx {i}: {direction} - ${transaction_value:.2f}")
        
        self.pattern_id += 1
        logger.info(f"Created back-forth scenario: {len(transactions)} transactions")
        return transactions
    
    async def create_circular_scenario(self,
                                     addresses: List[str],
                                     pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """
        Cria cenário circular realista A→B→C→A
        
        Características:
        - Volume preservado (~95%)
        - Timing suspeito (intervalos regulares)
        - Mesmo valor percorre o ciclo
        """
        config = PatternConfig(**pattern_config)
        transactions = []
        
        if len(addresses) < 3:
            addresses = addresses + [f"0x{uuid.uuid4().hex[:40]}" for _ in range(3 - len(addresses))]
        
        base_time = datetime.utcnow() - timedelta(hours=1)
        
        # Criar ciclos completos
        cycles = config.transaction_count // len(addresses)
        
        for cycle in range(cycles):
            current_value = config.base_value * (0.98 ** cycle)  # Pequena perda por ciclo
            
            for i in range(len(addresses)):
                from_addr = addresses[i]
                to_addr = addresses[(i + 1) % len(addresses)]  # Próximo no ciclo
                
                # Preservar volume com pequena variação
                value_variation = random.uniform(0.98, 1.02)  # ±2%
                transaction_value = current_value * value_variation
                
                # Timing regular (indicativo de bot/script)
                time_offset = (cycle * len(addresses) + i) * config.time_interval_minutes
                timestamp = base_time + timedelta(minutes=time_offset)
                
                transaction = TransactionData(
                    hash=f"0xcircular{self.pattern_id:03d}_{cycle:02d}_{i:02d}_{uuid.uuid4().hex[:8]}",
                    from_address=from_addr,
                    to_address=to_addr,
                    value=transaction_value,
                    gas_price=config.gas_price_base + random.uniform(-2, 2),
                    timestamp=timestamp,
                    block_number=18000000 + (cycle * len(addresses) + i) * 50,
                    transaction_type=TransactionType.TRANSFER
                )
                
                transactions.append(transaction)
                logger.debug(f"Created circular tx {cycle}-{i}: {from_addr[:8]}→{to_addr[:8]} - ${transaction_value:.2f}")
        
        self.pattern_id += 1
        logger.info(f"Created circular scenario: {len(transactions)} transactions, {cycles} cycles")
        return transactions
    
    async def create_self_trading_scenario(self,
                                         address: str,
                                         pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """
        Cria cenário de self-trading
        
        Simples: address → address
        """
        config = PatternConfig(**pattern_config)
        
        transaction = TransactionData(
            hash=f"0xself{self.pattern_id:03d}_{uuid.uuid4().hex[:12]}",
            from_address=address,
            to_address=address,
            value=config.base_value,
            gas_price=config.gas_price_base,
            timestamp=datetime.utcnow(),
            block_number=18000000,
            transaction_type=TransactionType.TRANSFER
        )
        
        self.pattern_id += 1
        logger.info(f"Created self-trading scenario: {address[:8]}→{address[:8]} - ${config.base_value}")
        return [transaction]


class EnhancedTestPatternFactory(TestPatternFactory):
    """
    Factory aprimorado com padrões mais sofisticados
    
    Implementa OCP: Extensível sem modificar classe base
    """
    
    async def create_layered_circular_scenario(self,
                                             addresses: List[str],
                                             pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """
        Cria padrão circular com múltiplas camadas
        A→B→C→A e A→D→E→A simultaneamente
        """
        base_transactions = await self.create_circular_scenario(addresses[:3], pattern_config)
        
        if len(addresses) >= 6:
            # Criar segundo ciclo
            second_layer = await self.create_circular_scenario(
                [addresses[0]] + addresses[3:6], 
                pattern_config
            )
            base_transactions.extend(second_layer)
        
        logger.info(f"Created layered circular scenario: {len(base_transactions)} transactions")
        return base_transactions
    
    async def create_sophisticated_back_forth(self,
                                            address_a: str,
                                            address_b: str,
                                            pattern_config: Dict[str, Any]) -> List[TransactionData]:
        """
        Back-and-forth com características mais realistas:
        - Volume increasing pattern
        - Time clustering
        - Gas price patterns
        """
        config = PatternConfig(**pattern_config)
        transactions = []
        
        base_time = datetime.utcnow() - timedelta(hours=3)
        
        # Criar clusters de atividade
        cluster_count = 3
        transactions_per_cluster = config.transaction_count // cluster_count
        
        for cluster in range(cluster_count):
            cluster_base_time = base_time + timedelta(hours=cluster)
            cluster_base_value = config.base_value * (1.1 ** cluster)  # Volume crescente
            
            for i in range(transactions_per_cluster):
                # Alternar direção dentro do cluster
                if i % 2 == 0:
                    from_addr, to_addr = address_a, address_b
                else:
                    from_addr, to_addr = address_b, address_a
                
                # Valor com padrão de crescimento
                transaction_value = cluster_base_value * (1 + (i * 0.02))
                
                # Tempo clustered (transações próximas no tempo)
                time_offset = i * 3 + random.randint(0, 2)  # 3 min interval ±2min
                timestamp = cluster_base_time + timedelta(minutes=time_offset)
                
                # Gas price com padrão
                gas_price = config.gas_price_base * (1 + cluster * 0.1)
                
                transaction = TransactionData(
                    hash=f"0xsophbf{self.pattern_id:03d}_{cluster:02d}_{i:02d}_{uuid.uuid4().hex[:8]}",
                    from_address=from_addr,
                    to_address=to_addr,
                    value=transaction_value,
                    gas_price=gas_price,
                    timestamp=timestamp,
                    block_number=18000000 + cluster * 1000 + i * 10,
                    transaction_type=TransactionType.TRANSFER
                )
                
                transactions.append(transaction)
        
        self.pattern_id += 1
        logger.info(f"Created sophisticated back-forth: {len(transactions)} transactions in {cluster_count} clusters")
        return transactions
