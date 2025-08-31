"""
Domain Services for Pattern Analysis
Implements business logic for fraud pattern detection following DDD principles
"""
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from data.models import TransactionData
from interfaces.data_providers import ITransactionHistoryProvider

logger = logging.getLogger(__name__)


@dataclass
class StructuringAnalysisResult:
    """
    Value Object para resultado de análise de estruturação
    
    Princípio: DDD Value Object - immutable, self-validating
    """
    is_detected: bool
    confidence_score: float
    total_amount: float
    transaction_count: int
    time_span_minutes: float
    pattern_details: Dict[str, any]
    transactions_involved: List[TransactionData]
    
    @property
    def is_structuring(self) -> bool:
        """Compatibilidade com código existente"""
        return self.is_detected
    
    @property
    def pattern_indicators(self) -> Dict[str, any]:
        """Compatibilidade com código existente"""
        return {
            "total_transactions": self.transaction_count,
            "total_value": self.total_amount,
            "time_span_minutes": self.time_span_minutes,
            **self.pattern_details
        }
    
    def __post_init__(self):
        """Validação automática do Value Object"""
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.transaction_count < 0:
            raise ValueError("Transaction count cannot be negative")
        if self.total_amount < 0:
            raise ValueError("Total amount cannot be negative")


class StructuringDetectionService:
    """
    Domain Service para detecção de estruturação (Multiple Small Transfers)
    
    Responsabilidade: Implementar lógica de negócio para detectar padrões de estruturação/smurfing
    Princípios: DDD Domain Service, Single Responsibility, Dependency Inversion
    """
    
    def __init__(self, transaction_provider: Optional[ITransactionHistoryProvider] = None):
        """
        Initialize service with optional transaction provider
        
        Args:
            transaction_provider: Provider para histórico de transações (DI)
        """
        self._transaction_provider = transaction_provider
        
    async def analyze_structuring_pattern(self, 
                                        transaction: TransactionData,
                                        config: Dict[str, any]) -> StructuringAnalysisResult:
        """
        Analisa padrão de estruturação em múltiplas transferências pequenas
        
        Args:
            transaction: Transação atual para análise
            config: Configuração da regra (time_window, min_count, etc.)
            
        Returns:
            Resultado da análise de estruturação
            
        Princípios: 
        - Single Responsibility: Foca apenas em detectar estruturação
        - Open/Closed: Extensível via diferentes algoritmos
        """
        try:
            # Extrair configurações
            time_window_minutes = config.get("time_window_minutes", 10)
            min_count = config.get("min_count", 10)
            max_individual_value = config.get("max_individual_value_usd", 9999)
            total_threshold = config.get("total_threshold_usd", 50000)
            
            # Verificar se transação atual se encaixa no padrão
            if transaction.value >= max_individual_value:
                return self._create_no_detection_result("Transaction value too high for structuring pattern")
            
            # Se temos provider de histórico, fazer análise completa
            if self._transaction_provider:
                return await self._analyze_with_history(transaction, config)
            else:
                # Análise simplificada sem histórico (para compatibilidade)
                return await self._analyze_without_history(transaction, config)
                
        except Exception as e:
            logger.error(f"Error in structuring analysis: {e}")
            return self._create_error_result(str(e))
    
    async def _analyze_with_history(self,
                                  transaction: TransactionData,
                                  config: Dict[str, any]) -> StructuringAnalysisResult:
        """
        Análise completa com histórico de transações
        
        Princípio: Strategy Pattern - algoritmo específico para análise com histórico
        """
        time_window_minutes = config.get("time_window_minutes", 10)
        min_count = config.get("min_count", 10)
        max_individual_value = config.get("max_individual_value_usd", 9999)
        total_threshold = config.get("total_threshold_usd", 50000)
        
        # Buscar transações recentes do endereço de origem
        recent_transactions = await self._transaction_provider.get_transactions_by_value_range(
            address=transaction.from_address,
            min_value=0,
            max_value=max_individual_value,
            time_window_minutes=time_window_minutes
        )
        
        # Incluir transação atual
        all_transactions = recent_transactions + [transaction]
        
        # Filtrar transações que se encaixam no padrão
        structured_transactions = [
            tx for tx in all_transactions 
            if tx.value < max_individual_value and tx.value > 0
        ]
        
        # Analisar padrão
        if len(structured_transactions) >= min_count:
            total_amount = sum(tx.value for tx in structured_transactions)
            
            if total_amount >= total_threshold:
                # Calcular métricas do padrão
                time_span = self._calculate_time_span(structured_transactions)
                confidence = self._calculate_confidence_score(
                    structured_transactions, config
                )
                
                pattern_details = {
                    "algorithm": "history_based",
                    "average_transaction_value": total_amount / len(structured_transactions),
                    "value_consistency": self._calculate_value_consistency(structured_transactions),
                    "timing_pattern": self._analyze_timing_pattern(structured_transactions),
                    "total_vs_threshold_ratio": total_amount / total_threshold
                }
                
                return StructuringAnalysisResult(
                    is_detected=True,
                    confidence_score=confidence,
                    total_amount=total_amount,
                    transaction_count=len(structured_transactions),
                    time_span_minutes=time_span.total_seconds() / 60,
                    pattern_details=pattern_details,
                    transactions_involved=structured_transactions
                )
        
        return self._create_no_detection_result("Insufficient transactions for structuring pattern")
    
    async def _analyze_without_history(self,
                                     transaction: TransactionData,
                                     config: Dict[str, any]) -> StructuringAnalysisResult:
        """
        Análise simplificada sem histórico (heurística)
        
        Princípio: Graceful degradation - funciona mesmo sem provider completo
        """
        max_individual_value = config.get("max_individual_value_usd", 9999)
        
        # Heurística simples: transação individual suspeita se for próxima ao limite
        upper_threshold = max_individual_value * 0.8  # 80% do limite
        lower_threshold = max_individual_value * 0.5  # 50% do limite
        
        if lower_threshold <= transaction.value <= upper_threshold:
            # Transação suspeita de ser parte de estruturação
            confidence = self._calculate_heuristic_confidence(transaction, config)
            
            pattern_details = {
                "algorithm": "heuristic_based", 
                "value_near_threshold": True,
                "threshold_ratio": transaction.value / max_individual_value,
                "warning": "Limited analysis without transaction history"
            }
            
            return StructuringAnalysisResult(
                is_detected=True,
                confidence_score=confidence,
                total_amount=transaction.value,
                transaction_count=1,
                time_span_minutes=0.0,
                pattern_details=pattern_details,
                transactions_involved=[transaction]
            )
        
        return self._create_no_detection_result("Transaction value not suspicious for structuring")
    
    def _calculate_confidence_score(self, 
                                   transactions: List[TransactionData],
                                   config: Dict[str, any]) -> float:
        """
        Calcula score de confiança baseado em múltiplos fatores
        
        Princípio: Single Responsibility - método focado em calcular confiança
        """
        if not transactions:
            return 0.0
        
        # Fatores para confidence score
        factors = []
        
        # 1. Quantidade de transações (mais = maior confiança)
        min_count = config.get("min_count", 10)
        count_factor = min(len(transactions) / min_count, 1.0)
        factors.append(count_factor * 0.3)  # 30% do score
        
        # 2. Consistência de valores (valores similares = maior confiança)
        value_consistency = self._calculate_value_consistency(transactions)
        factors.append(value_consistency * 0.3)  # 30% do score
        
        # 3. Padrão temporal (frequência regular = maior confiança)
        timing_score = self._analyze_timing_pattern(transactions)
        factors.append(timing_score * 0.2)  # 20% do score
        
        # 4. Proximidade aos thresholds (próximo ao limite = maior confiança)
        max_individual = config.get("max_individual_value_usd", 9999)
        threshold_score = self._calculate_threshold_proximity(transactions, max_individual)
        factors.append(threshold_score * 0.2)  # 20% do score
        
        # Combinar fatores
        final_score = sum(factors)
        return min(max(final_score, 0.0), 1.0)  # Clamp entre 0.0 e 1.0
    
    def _calculate_heuristic_confidence(self,
                                      transaction: TransactionData,
                                      config: Dict[str, any]) -> float:
        """
        Calcula confiança heurística para análise sem histórico
        """
        max_individual = config.get("max_individual_value_usd", 9999)
        threshold_ratio = transaction.value / max_individual
        
        # Maior confiança quando mais próximo do threshold
        if threshold_ratio >= 0.8:
            return 0.7  # Alta confiança
        elif threshold_ratio >= 0.6:
            return 0.5  # Média confiança
        else:
            return 0.3  # Baixa confiança
    
    def _calculate_value_consistency(self, transactions: List[TransactionData]) -> float:
        """Calcula consistência dos valores das transações"""
        if len(transactions) < 2:
            return 0.5
        
        values = [tx.value for tx in transactions]
        avg_value = sum(values) / len(values)
        
        # Calcular desvio padrão relativo
        variance = sum((v - avg_value) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        if avg_value > 0:
            coefficient_of_variation = std_dev / avg_value
            # Menor variação = maior consistência
            consistency = max(0.0, 1.0 - coefficient_of_variation)
            return min(consistency, 1.0)
        
        return 0.0
    
    def _analyze_timing_pattern(self, transactions: List[TransactionData]) -> float:
        """Analisa padrão temporal das transações"""
        if len(transactions) < 3:
            return 0.5
        
        # Ordenar por timestamp
        sorted_txs = sorted(transactions, key=lambda tx: tx.timestamp)
        
        # Calcular intervalos entre transações
        intervals = []
        for i in range(1, len(sorted_txs)):
            interval = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return 0.5
        
        # Calcular consistência dos intervalos
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((interval - avg_interval) ** 2 for interval in intervals) / len(intervals)
        std_dev = variance ** 0.5
        
        if avg_interval > 0:
            coefficient_of_variation = std_dev / avg_interval
            # Intervalos regulares = padrão mais suspeito
            regularity = max(0.0, 1.0 - coefficient_of_variation)
            return min(regularity, 1.0)
        
        return 0.0
    
    def _calculate_threshold_proximity(self, 
                                     transactions: List[TransactionData],
                                     max_individual: float) -> float:
        """Calcula quão próximas as transações estão do threshold"""
        if not transactions:
            return 0.0
        
        proximities = []
        for tx in transactions:
            ratio = tx.value / max_individual
            # Maior score para valores próximos ao threshold (0.7-0.9)
            if 0.7 <= ratio <= 0.9:
                proximities.append(1.0)
            elif 0.5 <= ratio < 0.7:
                proximities.append(0.7)
            elif 0.9 < ratio <= 1.0:
                proximities.append(0.8)
            else:
                proximities.append(0.3)
        
        return sum(proximities) / len(proximities)
    
    def _calculate_time_span(self, transactions: List[TransactionData]) -> timedelta:
        """Calcula span temporal das transações"""
        if not transactions:
            return timedelta(0)
        
        timestamps = [tx.timestamp for tx in transactions]
        return max(timestamps) - min(timestamps)
    
    def _create_no_detection_result(self, reason: str) -> StructuringAnalysisResult:
        """Helper para criar resultado negativo"""
        return StructuringAnalysisResult(
            is_detected=False,
            confidence_score=0.0,
            total_amount=0.0,
            transaction_count=0,
            time_span_minutes=0.0,
            pattern_details={"reason": reason},
            transactions_involved=[]
        )
    
    def _create_error_result(self, error_message: str) -> StructuringAnalysisResult:
        """Helper para criar resultado de erro"""
        return StructuringAnalysisResult(
            is_detected=False,
            confidence_score=0.0,
            total_amount=0.0,
            transaction_count=0,
            time_span_minutes=0.0,
            pattern_details={"error": error_message},
            transactions_involved=[]
        )
