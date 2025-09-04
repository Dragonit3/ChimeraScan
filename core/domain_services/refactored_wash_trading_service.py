"""
Refactored Advanced Wash Trading Detection Service
Implementa princípios SOLID com arquitetura limpa e extensível
"""
import asyncio
import logging
import uuid
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter

from interfaces.wash_trading import (
    IWashTradingDetector, WashTradingResult, WashTradingPattern, WashTradingType, AddressPair
)
from interfaces.data_sources import (
    ITransactionDataSource, TransactionRelationship
)
from data.models import TransactionData

logger = logging.getLogger(__name__)


class RefactoredWashTradingDetectionService(IWashTradingDetector):
    """
    Serviço refatorado seguindo princípios SOLID rigorosamente
    
    Implementa:
    - SRP: Uma responsabilidade - coordenar detecção
    - OCP: Extensível via strategy pattern
    - LSP: Substituível por outras implementações
    - ISP: Interfaces segregadas
    - DIP: Depende de abstrações, não implementações
    """
    
    def __init__(self, 
                 data_source: ITransactionDataSource,
                 detection_strategies: Optional[Dict[str, 'IWashTradingStrategy']] = None):
        """
        Injeta dependências através de abstrações (DIP)
        
        Args:
            data_source: Fonte de dados (abstração)
            detection_strategies: Estratégias de detecção (Strategy Pattern)
        """
        self.data_source = data_source
        self.strategies = detection_strategies or self._create_default_strategies()
        
        # Métricas e cache
        self.detection_stats = {
            "total_analyzed": 0,
            "patterns_detected": 0,
            "average_confidence": 0.0,
            "strategy_usage": defaultdict(int)
        }
        
        self._result_cache: Dict[str, WashTradingResult] = {}
        
        logger.info("RefactoredWashTradingDetectionService initialized with DIP")
    
    async def analyze_transaction(self, 
                                transaction: TransactionData,
                                config: Dict[str, Any]) -> WashTradingResult:
        """
        Coordena análise usando strategy pattern
        
        Implementa Template Method Pattern para pipeline de análise
        """
        start_time = datetime.utcnow()
        cache_key = self._generate_cache_key(transaction)
        
        # Check cache first
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]
        
        try:
            # Pipeline de análise usando Template Method
            context = await self._gather_analysis_context(transaction, config)
            patterns = await self._execute_detection_strategies(context, config)
            result = await self._synthesize_final_result(patterns, transaction, start_time)
            
            # Cache result
            self._result_cache[cache_key] = result
            self._update_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in refactored wash trading analysis: {e}")
            return self._create_empty_result(transaction, start_time)
    
    async def analyze_address_pair(self,
                                 address_a: str,
                                 address_b: str,
                                 time_window: timedelta) -> AddressPair:
        """
        Delega análise para data source (SRP)
        """
        relationships = await self.data_source.get_address_relationships(
            address_a, time_window, min_interactions=1
        )
        
        # Find specific relationship
        for rel in relationships:
            if rel.address_b.lower() == address_b.lower():
                return self._convert_to_address_pair(rel)
        
        # Return empty relationship if not found
        return AddressPair(
            address_a=address_a,
            address_b=address_b,
            relationship_score=0.0,
            transaction_count=0,
            total_volume=0.0,
            avg_transaction_value=0.0,
            first_interaction=datetime.utcnow(),
            last_interaction=datetime.utcnow(),
            interaction_frequency=0.0
        )
    
    async def _gather_analysis_context(self, 
                                     transaction: TransactionData,
                                     config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Template Method: Gather context for analysis
        """
        context = {
            "transaction": transaction,
            "config": config,
            "timestamp": datetime.utcnow()
        }
        
        # Gather historical data if needed
        time_window = timedelta(hours=config.get("analysis_window_hours", 24))
        
        context["transaction_history"] = await self.data_source.get_transaction_history(
            transaction.from_address, time_window
        )
        
        context["address_relationships"] = await self.data_source.get_address_relationships(
            transaction.from_address, time_window
        )
        
        # Add destination analysis if not self-trading
        if transaction.to_address and transaction.from_address != transaction.to_address:
            context["destination_history"] = await self.data_source.get_transaction_history(
                transaction.to_address, time_window
            )
        
        # Check for circular paths
        if config.get("algorithms", {}).get("circular_detection", {}).get("enabled", False):
            max_hops = config["algorithms"]["circular_detection"].get("max_hops", 5)
            context["circular_paths"] = await self.data_source.find_circular_paths(
                transaction.from_address, max_hops, time_window
            )
        
        return context
    
    async def _execute_detection_strategies(self,
                                          context: Dict[str, Any],
                                          config: Dict[str, Any]) -> List[WashTradingPattern]:
        """
        Template Method: Execute all enabled strategies
        """
        patterns = []
        algorithms_config = config.get("algorithms", {})
        
        for strategy_name, strategy in self.strategies.items():
            if algorithms_config.get(strategy_name, {}).get("enabled", True):
                try:
                    strategy_patterns = await strategy.detect_patterns(context, algorithms_config)
                    patterns.extend(strategy_patterns)
                    self.detection_stats["strategy_usage"][strategy_name] += 1
                    
                except Exception as e:
                    logger.error(f"Error in strategy {strategy_name}: {e}")
        
        return patterns
    
    async def _synthesize_final_result(self,
                                     patterns: List[WashTradingPattern],
                                     transaction: TransactionData,
                                     start_time: datetime) -> WashTradingResult:
        """
        Template Method: Synthesize final result from all patterns
        """
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if not patterns:
            return WashTradingResult(
                is_detected=False,
                confidence_score=0.0,
                patterns_found=[],
                analysis_details={"no_patterns_detected": True},
                processing_time_ms=processing_time,
                algorithm_used="refactored_service_v1"
            )
        
        # Calculate overall confidence using weighted average
        total_confidence = sum(p.confidence_score for p in patterns)
        weighted_confidence = min(1.0, total_confidence / len(patterns) * 1.2)  # Slight boost
        
        # Prepare analysis details
        analysis_details = {
            "patterns_analyzed": len(patterns),
            "highest_confidence": max(p.confidence_score for p in patterns),
            "pattern_types": [p.pattern_type.value for p in patterns],
            "total_volume_analyzed": sum(p.total_volume for p in patterns),
            "processing_time_ms": processing_time
        }
        
        return WashTradingResult(
            is_detected=True,
            confidence_score=weighted_confidence,
            patterns_found=patterns,
            analysis_details=analysis_details,
            processing_time_ms=processing_time,
            algorithm_used="refactored_service_v1"
        )
    
    def _create_default_strategies(self) -> Dict[str, 'IWashTradingStrategy']:
        """
        Factory method for creating default strategies (Factory Pattern)
        """
        return {
            "self_trading": SelfTradingStrategy(),
            "back_and_forth": BackAndForthStrategy(),
            "circular_detection": CircularDetectionStrategy()
        }
    
    def _generate_cache_key(self, transaction: TransactionData) -> str:
        """Generate deterministic cache key"""
        return f"{transaction.hash}_{transaction.from_address}_{transaction.to_address}"[:64]
    
    def _create_empty_result(self, transaction: TransactionData, start_time: datetime) -> WashTradingResult:
        """Create empty result for error cases"""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return WashTradingResult(
            is_detected=False,
            confidence_score=0.0,
            patterns_found=[],
            analysis_details={"error": "Analysis failed"},
            processing_time_ms=processing_time,
            algorithm_used="refactored_service_v1"
        )
    
    def _convert_to_address_pair(self, relationship: TransactionRelationship) -> AddressPair:
        """Convert relationship to address pair"""
        return AddressPair(
            address_a=relationship.address_a,
            address_b=relationship.address_b,
            relationship_score=relationship.relationship_score,
            transaction_count=len(relationship.transactions),
            total_volume=relationship.total_volume,
            avg_transaction_value=relationship.total_volume / len(relationship.transactions) if relationship.transactions else 0.0,
            first_interaction=relationship.first_interaction,
            last_interaction=relationship.last_interaction,
            interaction_frequency=relationship.interaction_frequency
        )
    
    def _update_stats(self, result: WashTradingResult):
        """Update internal statistics"""
        self.detection_stats["total_analyzed"] += 1
        
        if result.is_detected:
            self.detection_stats["patterns_detected"] += 1
        
        # Running average of confidence
        current_avg = self.detection_stats["average_confidence"]
        total = self.detection_stats["total_analyzed"]
        new_avg = ((current_avg * (total - 1)) + result.confidence_score) / total
        self.detection_stats["average_confidence"] = new_avg
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get current detection statistics"""
        return dict(self.detection_stats)


# Strategy Pattern Implementation
from abc import ABC, abstractmethod

class IWashTradingStrategy(ABC):
    """
    Interface para estratégias de detecção (Strategy Pattern)
    
    Implementa ISP: Interface segregada para cada estratégia
    """
    
    @abstractmethod
    async def detect_patterns(self, 
                            context: Dict[str, Any],
                            config: Dict[str, Any]) -> List[WashTradingPattern]:
        """Detecta padrões específicos da estratégia"""
        pass


class SelfTradingStrategy(IWashTradingStrategy):
    """
    Estratégia para detecção de self-trading
    
    Implementa SRP: Responsabilidade única - detectar self-trading
    """
    
    async def detect_patterns(self, 
                            context: Dict[str, Any],
                            config: Dict[str, Any]) -> List[WashTradingPattern]:
        """Detecta padrões de self-trading"""
        transaction = context["transaction"]
        
        if transaction.to_address and transaction.from_address.lower() == transaction.to_address.lower():
            pattern = WashTradingPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type=WashTradingType.SELF_TRADING,
                involved_addresses=[transaction.from_address],
                transaction_hashes=[transaction.hash],
                total_volume=transaction.value,
                transaction_count=1,
                time_span_minutes=0.0,
                confidence_score=1.0,  # 100% confidence for self-trading
                detection_algorithm="self_trading_strategy_v1",
                first_detected=datetime.utcnow(),
                last_activity=transaction.timestamp,
                context_data={
                    "direct_self_trading": True,
                    "detection_method": "address_comparison"
                }
            )
            return [pattern]
        
        return []


class BackAndForthStrategy(IWashTradingStrategy):
    """
    Estratégia para detecção de back-and-forth
    
    Implementa SRP: Responsabilidade única - detectar vai-e-volta
    """
    
    async def detect_patterns(self, 
                            context: Dict[str, Any],
                            config: Dict[str, Any]) -> List[WashTradingPattern]:
        """Detecta padrões de back-and-forth usando dados históricos reais"""
        patterns = []
        transaction = context["transaction"]
        relationships = context.get("address_relationships", [])
        back_forth_config = config.get("back_and_forth", {})
        
        min_alternations = back_forth_config.get("min_alternations", 6)
        min_confidence = back_forth_config.get("min_confidence", 0.75)
        
        for relationship in relationships:
            # Verificar se é relacionamento com destino da transação atual
            if (transaction.to_address and 
                relationship.address_b.lower() == transaction.to_address.lower()):
                
                # Analisar padrão de alternação
                alternation_score = relationship.pattern_indicators.get("alternating_pattern", 0.0)
                volume_similarity = relationship.pattern_indicators.get("volume_similarity", 0.0)
                timing_regularity = relationship.pattern_indicators.get("timing_regularity", 0.0)
                
                # Calcular confiança combinada
                confidence = (alternation_score * 0.5 + 
                            volume_similarity * 0.3 + 
                            timing_regularity * 0.2)
                
                # Verificar se atende critérios
                if (len(relationship.transactions) >= min_alternations and 
                    confidence >= min_confidence):
                    
                    pattern = WashTradingPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=WashTradingType.BACK_AND_FORTH,
                        involved_addresses=[relationship.address_a, relationship.address_b],
                        transaction_hashes=[tx.hash for tx in relationship.transactions],
                        total_volume=relationship.total_volume,
                        transaction_count=len(relationship.transactions),
                        time_span_minutes=(relationship.last_interaction - 
                                         relationship.first_interaction).total_seconds() / 60,
                        confidence_score=confidence,
                        detection_algorithm="back_and_forth_strategy_v1",
                        first_detected=datetime.utcnow(),
                        last_activity=relationship.last_interaction,
                        context_data={
                            "alternation_score": alternation_score,
                            "volume_similarity": volume_similarity,
                            "timing_regularity": timing_regularity,
                            "interaction_frequency": relationship.interaction_frequency
                        }
                    )
                    patterns.append(pattern)
        
        return patterns


class CircularDetectionStrategy(IWashTradingStrategy):
    """
    Estratégia para detecção de padrões circulares
    
    Implementa SRP: Responsabilidade única - detectar círculos
    """
    
    async def detect_patterns(self, 
                            context: Dict[str, Any],
                            config: Dict[str, Any]) -> List[WashTradingPattern]:
        """Detecta padrões circulares usando dados de caminhos"""
        patterns = []
        circular_paths = context.get("circular_paths", [])
        circular_config = config.get("circular_detection", {})
        
        min_confidence = circular_config.get("min_confidence", 0.80)
        preservation_threshold = circular_config.get("value_preservation_threshold", 0.95)
        
        for path in circular_paths:
            if (path.cycle_complete and 
                path.volume_preservation_ratio >= preservation_threshold):
                
                # Calcular confiança baseada em preservação de volume e regularidade
                volume_confidence = path.volume_preservation_ratio
                timing_confidence = max(0.0, 1.0 - (path.time_span.total_seconds() / 3600) / 24)  # Penalty for long spans
                path_confidence = min(1.0, path.hop_count / 5.0)  # More hops = higher confidence
                
                overall_confidence = (volume_confidence * 0.5 + 
                                    timing_confidence * 0.3 + 
                                    path_confidence * 0.2)
                
                if overall_confidence >= min_confidence:
                    pattern = WashTradingPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=WashTradingType.CIRCULAR,
                        involved_addresses=path.involved_addresses,
                        transaction_hashes=[tx.hash for tx in path.path_transactions],
                        total_volume=path.total_volume,
                        transaction_count=len(path.path_transactions),
                        time_span_minutes=path.time_span.total_seconds() / 60,
                        confidence_score=overall_confidence,
                        detection_algorithm="circular_detection_strategy_v1",
                        first_detected=datetime.utcnow(),
                        last_activity=max(tx.timestamp for tx in path.path_transactions),
                        context_data={
                            "volume_preservation_ratio": path.volume_preservation_ratio,
                            "hop_count": path.hop_count,
                            "cycle_complete": path.cycle_complete,
                            "timing_confidence": timing_confidence
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
