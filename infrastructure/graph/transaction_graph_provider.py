"""
Advanced Transaction Graph Provider
Implementa análise avançada de grafo de transações para detecção de wash trading
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib

from interfaces.wash_trading import ITransactionGraphProvider, AddressPair
from data.models import TransactionData

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    """Nó no grafo de transações"""
    address: str
    connections: Set[str]
    total_volume: float
    transaction_count: int
    first_seen: datetime
    last_seen: datetime

@dataclass
class TransactionPath:
    """Caminho de transações no grafo"""
    path: List[str]  # Sequência de endereços
    transactions: List[TransactionData]
    total_volume: float
    volume_preservation_ratio: float
    time_span: timedelta
    is_circular: bool

class AdvancedTransactionGraphProvider(ITransactionGraphProvider):
    """
    Provedor avançado de análise de grafo de transações
    
    Implementa algoritmos sofisticados de grafo para detecção de padrões complexos:
    - BFS/DFS para encontrar caminhos
    - Detecção de ciclos
    - Análise de preservação de volume
    - Cache inteligente para performance
    
    Princípios SOLID:
    - SRP: Foca apenas em análise de grafo
    - OCP: Extensível para novos algoritmos de grafo
    - DIP: Implementa interface abstrata
    """
    
    def __init__(self, max_cache_size: int = 10000):
        self.max_cache_size = max_cache_size
        
        # Cache multinível para otimização
        self._relationship_cache: Dict[Tuple[str, str], AddressPair] = {}
        self._path_cache: Dict[Tuple[str, str, int], List[List[TransactionData]]] = {}
        self._graph_cache: Dict[str, GraphNode] = {}
        
        # Métricas para monitoramento
        self._cache_hits = 0
        self._cache_misses = 0
        self._graph_queries = 0
        
        logger.info("AdvancedTransactionGraphProvider initialized")
    
    async def get_address_relationships(self, 
                                      address: str,
                                      depth: int = 2,
                                      time_window: timedelta = timedelta(hours=24)) -> List[AddressPair]:
        """
        Implementa análise avançada de relacionamentos usando BFS
        
        Args:
            address: Endereço para analisar
            depth: Profundidade da busca no grafo
            time_window: Janela de tempo para considerar
            
        Returns:
            Lista de relacionamentos encontrados ordenados por relevância
        """
        self._graph_queries += 1
        
        try:
            # BFS para encontrar relacionamentos até a profundidade especificada
            visited = set()
            queue = deque([(address, 0)])  # (endereço, profundidade)
            relationships = []
            
            while queue:
                current_address, current_depth = queue.popleft()
                
                if current_address in visited or current_depth >= depth:
                    continue
                
                visited.add(current_address)
                
                # Obter conexões diretas do endereço atual
                direct_connections = await self._get_direct_connections(
                    current_address, time_window
                )
                
                for connected_address in direct_connections:
                    if connected_address not in visited:
                        # Calcular relacionamento
                        relationship = await self._calculate_relationship(
                            current_address, connected_address, time_window
                        )
                        
                        if relationship.relationship_score > 0.1:  # Threshold mínimo
                            relationships.append(relationship)
                        
                        # Adicionar à queue para próxima profundidade
                        if current_depth + 1 < depth:
                            queue.append((connected_address, current_depth + 1))
            
            # Ordenar por relevância (score + volume)
            relationships.sort(
                key=lambda r: r.relationship_score * r.total_volume, 
                reverse=True
            )
            
            logger.debug(f"Found {len(relationships)} relationships for {address[:8]}... at depth {depth}")
            return relationships[:50]  # Limitar resultados
            
        except Exception as e:
            logger.error(f"Error in relationship analysis for {address}: {e}")
            return []
    
    async def find_transaction_paths(self,
                                   from_address: str,
                                   to_address: str,
                                   max_hops: int = 5,
                                   time_window: timedelta = timedelta(hours=24)) -> List[List[TransactionData]]:
        """
        Encontra caminhos de transações usando algoritmo DFS modificado
        
        Implementa detecção de ciclos e análise de preservação de volume
        """
        cache_key = (from_address, to_address, max_hops)
        
        # Verificar cache
        if cache_key in self._path_cache:
            self._cache_hits += 1
            return self._path_cache[cache_key]
        
        self._cache_misses += 1
        
        try:
            paths = []
            
            # DFS para encontrar todos os caminhos possíveis
            await self._dfs_find_paths(
                current=from_address,
                target=to_address,
                path=[from_address],
                visited=set([from_address]),
                transactions_path=[],
                max_hops=max_hops,
                time_window=time_window,
                found_paths=paths
            )
            
            # Filtrar e ranquear caminhos por relevância
            ranked_paths = await self._rank_transaction_paths(paths)
            
            # Cache resultado
            if len(self._path_cache) < self.max_cache_size:
                self._path_cache[cache_key] = ranked_paths
            
            logger.debug(f"Found {len(ranked_paths)} paths from {from_address[:8]}... to {to_address[:8]}...")
            return ranked_paths
            
        except Exception as e:
            logger.error(f"Error finding paths from {from_address} to {to_address}: {e}")
            return []
    
    async def _get_direct_connections(self, address: str, time_window: timedelta) -> List[str]:
        """
        Simula obtenção de conexões diretas de um endereço
        
        Em implementação real, consultaria banco de dados de transações
        """
        # Simulação determinística baseada no endereço
        seed = int(hashlib.md5(address.encode()).hexdigest(), 16) % (2**32)
        import random
        random.seed(seed)
        
        # Gerar 5-15 conexões simuladas
        num_connections = random.randint(5, 15)
        connections = []
        
        for i in range(num_connections):
            # Gerar endereço conectado
            connection_seed = f"{address}_{i}"
            connection_hash = hashlib.md5(connection_seed.encode()).hexdigest()
            connection_address = f"0x{connection_hash[:40]}"
            connections.append(connection_address)
        
        return connections
    
    async def _calculate_relationship(self, 
                                    address_a: str, 
                                    address_b: str, 
                                    time_window: timedelta) -> AddressPair:
        """
        Calcula relacionamento avançado entre dois endereços
        """
        cache_key = (address_a, address_b)
        
        # Verificar cache
        if cache_key in self._relationship_cache:
            return self._relationship_cache[cache_key]
        
        # Simulação de análise avançada
        seed = int(hashlib.md5(f"{address_a}{address_b}".encode()).hexdigest(), 16) % (2**32)
        import random
        random.seed(seed)
        
        # Métricas simuladas mais realistas
        transaction_count = random.randint(3, 25)
        
        # Volume baseado em padrões mais realistas
        if transaction_count > 15:  # Muitas transações
            avg_value = random.uniform(5000, 30000)
            relationship_score = random.uniform(0.7, 0.95)
        elif transaction_count > 8:  # Transações moderadas
            avg_value = random.uniform(10000, 80000)
            relationship_score = random.uniform(0.4, 0.8)
        else:  # Poucas transações
            avg_value = random.uniform(1000, 20000)
            relationship_score = random.uniform(0.1, 0.5)
        
        total_volume = transaction_count * avg_value
        
        # Timestamps mais realistas
        now = datetime.utcnow()
        first_interaction = now - timedelta(minutes=random.randint(60, int(time_window.total_seconds() / 60)))
        last_interaction = now - timedelta(minutes=random.randint(5, 60))
        
        # Frequência calculada
        time_span_hours = max(0.1, (last_interaction - first_interaction).total_seconds() / 3600)
        interaction_frequency = transaction_count / time_span_hours
        
        relationship = AddressPair(
            address_a=address_a,
            address_b=address_b,
            relationship_score=relationship_score,
            transaction_count=transaction_count,
            total_volume=total_volume,
            avg_transaction_value=avg_value,
            first_interaction=first_interaction,
            last_interaction=last_interaction,
            interaction_frequency=interaction_frequency
        )
        
        # Cache resultado
        if len(self._relationship_cache) < self.max_cache_size:
            self._relationship_cache[cache_key] = relationship
        
        return relationship
    
    async def _dfs_find_paths(self,
                            current: str,
                            target: str,
                            path: List[str],
                            visited: Set[str],
                            transactions_path: List[TransactionData],
                            max_hops: int,
                            time_window: timedelta,
                            found_paths: List[List[TransactionData]]):
        """
        DFS recursivo para encontrar caminhos
        """
        if len(path) > max_hops + 1:  # +1 porque path inclui origem
            return
        
        if current == target and len(path) > 1:
            # Encontrou caminho válido
            found_paths.append(transactions_path.copy())
            return
        
        if len(path) > max_hops:
            return
        
        # Obter conexões do endereço atual
        connections = await self._get_direct_connections(current, time_window)
        
        for next_address in connections:
            if next_address not in visited or (next_address == target and len(path) > 1):
                # Simular transação entre current e next_address
                simulated_tx = await self._create_simulated_transaction(current, next_address)
                
                new_visited = visited.copy()
                new_visited.add(next_address)
                
                await self._dfs_find_paths(
                    current=next_address,
                    target=target,
                    path=path + [next_address],
                    visited=new_visited,
                    transactions_path=transactions_path + [simulated_tx],
                    max_hops=max_hops,
                    time_window=time_window,
                    found_paths=found_paths
                )
                
                # Limitar número total de caminhos para performance
                if len(found_paths) >= 50:
                    break
    
    async def _create_simulated_transaction(self, from_addr: str, to_addr: str) -> TransactionData:
        """Cria transação simulada para análise de caminho"""
        from data.models import TransactionType
        import uuid
        
        # Gerar dados determinísticos
        seed = int(hashlib.md5(f"{from_addr}{to_addr}".encode()).hexdigest(), 16) % (2**32)
        import random
        random.seed(seed)
        
        return TransactionData(
            hash=f"0x{uuid.uuid4().hex}",
            from_address=from_addr,
            to_address=to_addr,
            value=random.uniform(5000, 50000),
            gas_price=random.uniform(20, 100),
            timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
            block_number=random.randint(1000000, 2000000),
            transaction_type=TransactionType.TRANSFER
        )
    
    async def _rank_transaction_paths(self, paths: List[List[TransactionData]]) -> List[List[TransactionData]]:
        """
        Ranqueia caminhos por relevância para wash trading
        
        Critérios:
        - Preservação de volume
        - Circularidade 
        - Tempo decorrido
        - Número de hops
        """
        ranked = []
        
        for path in paths:
            if not path:
                continue
            
            # Calcular métricas do caminho
            total_volume = sum(tx.value for tx in path)
            initial_volume = path[0].value
            final_volume = path[-1].value if len(path) > 1 else initial_volume
            
            # Volume preservation ratio
            volume_preservation = final_volume / initial_volume if initial_volume > 0 else 0
            
            # Time span
            if len(path) > 1:
                time_span = path[-1].timestamp - path[0].timestamp
                time_span_minutes = time_span.total_seconds() / 60
            else:
                time_span_minutes = 0
            
            # Circularidade (se primeiro e último endereço são iguais)
            is_circular = len(path) > 1 and path[0].from_address == path[-1].to_address
            
            # Score composto
            score = 0.0
            
            # Maior score para alta preservação de volume
            if volume_preservation > 0.9:
                score += 0.4
            elif volume_preservation > 0.7:
                score += 0.2
            
            # Maior score para circularidade
            if is_circular:
                score += 0.3
            
            # Menor score para caminhos muito longos (menos provável)
            if len(path) <= 3:
                score += 0.2
            elif len(path) <= 5:
                score += 0.1
            
            # Maior score para timespan suspeito (muito rápido)
            if time_span_minutes < 60:  # Menos de 1 hora
                score += 0.1
            
            ranked.append((score, path))
        
        # Ordenar por score descendente
        ranked.sort(key=lambda x: x[0], reverse=True)
        
        return [path for score, path in ranked[:20]]  # Top 20 caminhos
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Retorna estatísticas do cache para monitoramento"""
        total_queries = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_queries if total_queries > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "graph_queries": self._graph_queries,
            "relationship_cache_size": len(self._relationship_cache),
            "path_cache_size": len(self._path_cache),
            "graph_cache_size": len(self._graph_cache)
        }
    
    async def clear_cache(self):
        """Limpa todos os caches"""
        self._relationship_cache.clear()
        self._path_cache.clear()
        self._graph_cache.clear()
        logger.info("All caches cleared")

class CircularPatternDetector:
    """
    Detector especializado para padrões circulares de wash trading
    
    Implementa algoritmos avançados para detectar:
    - Ciclos simples (A->B->A)  
    - Ciclos complexos (A->B->C->D->A)
    - Preservação de volume em ciclos
    - Padrões temporais suspeitos
    """
    
    def __init__(self, graph_provider: AdvancedTransactionGraphProvider):
        self.graph_provider = graph_provider
        self.detection_stats = {
            "cycles_found": 0,
            "suspicious_cycles": 0,
            "total_volume_analyzed": 0.0
        }
    
    async def detect_circular_patterns(self,
                                     transaction: TransactionData,
                                     config: Dict[str, any]) -> List[TransactionPath]:
        """
        Detecta padrões circulares avançados
        
        Args:
            transaction: Transação atual para análise
            config: Configuração do algoritmo circular
            
        Returns:
            Lista de padrões circulares detectados
        """
        try:
            circular_config = config.get("algorithms", {}).get("circular_detection", {})
            max_hops = circular_config.get("max_hops", 5)
            time_window_minutes = circular_config.get("time_window_minutes", 60)
            min_transactions = circular_config.get("min_transactions_in_cycle", 3)
            preservation_threshold = circular_config.get("value_preservation_threshold", 0.95)
            
            time_window = timedelta(minutes=time_window_minutes)
            
            # Buscar caminhos que retornam ao endereço original
            circular_paths = await self.graph_provider.find_transaction_paths(
                from_address=transaction.from_address,
                to_address=transaction.from_address,  # Mesmo endereço = circular
                max_hops=max_hops,
                time_window=time_window
            )
            
            detected_patterns = []
            
            for path in circular_paths:
                if len(path) >= min_transactions:
                    # Analisar se o caminho é suspeito
                    pattern = await self._analyze_circular_path(
                        path, transaction, preservation_threshold
                    )
                    
                    if pattern and pattern.volume_preservation_ratio >= preservation_threshold:
                        detected_patterns.append(pattern)
                        self.detection_stats["suspicious_cycles"] += 1
            
            self.detection_stats["cycles_found"] += len(circular_paths)
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"Error in circular pattern detection: {e}")
            return []
    
    async def _analyze_circular_path(self,
                                   path: List[TransactionData],
                                   trigger_tx: TransactionData,
                                   preservation_threshold: float) -> Optional[TransactionPath]:
        """Analisa um caminho circular para determinar se é suspeito"""
        if not path:
            return None
        
        # Calcular preservação de volume
        initial_volume = path[0].value
        final_volume = path[-1].value
        total_volume = sum(tx.value for tx in path)
        
        volume_preservation = final_volume / initial_volume if initial_volume > 0 else 0
        
        # Calcular tempo decorrido
        time_span = path[-1].timestamp - path[0].timestamp
        
        # Verificar circularidade real
        is_circular = path[0].from_address.lower() == path[-1].to_address.lower()
        
        if is_circular and volume_preservation >= preservation_threshold:
            # Extrair endereços únicos no caminho
            addresses = [tx.from_address for tx in path]
            addresses.append(path[-1].to_address)
            unique_addresses = list(set(addresses))
            
            return TransactionPath(
                path=unique_addresses,
                transactions=path + [trigger_tx],  # Incluir transação que disparou
                total_volume=total_volume,
                volume_preservation_ratio=volume_preservation,
                time_span=time_span,
                is_circular=is_circular
            )
        
        return None
