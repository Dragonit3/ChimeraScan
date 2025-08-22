"""
Sistema de Pontuação de Risco
Implementa algoritmos de ML e análise de padrões para scoring de risco
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from config.settings import settings
from data.models import TransactionData, TransactionType
from interfaces.fraud_detection import IRiskScorer

logger = logging.getLogger(__name__)

@dataclass
class RiskFactor:
    """Fator individual de risco"""
    name: str
    score: float
    weight: float
    description: str
    evidence: Dict[str, Any]

class RiskScorer(IRiskScorer):
    """
    Sistema de pontuação de risco baseado em múltiplos fatores
    
    Combina análise de padrões, dados históricos e heurísticas
    para calcular score de risco de 0.0 a 1.0
    """
    
    def __init__(self):
        self.scoring_config = self._load_scoring_config()
        self.transaction_history = {}  # Cache de histórico recente
        logger.info("RiskScorer initialized")
    
    def _load_scoring_config(self) -> Dict[str, Any]:
        """Carrega configuração de scoring de risco"""
        # Valores padrão - idealmente viriam de arquivo de configuração
        return {
            "wallet_age": {"weight": 0.15, "new_threshold_hours": 168},
            "transaction_frequency": {"weight": 0.20, "normal_range": [1, 50]},
            "value_patterns": {"weight": 0.25, "round_number_penalty": 0.1},
            "time_patterns": {"weight": 0.15, "off_hours_penalty": 0.2},
            "network_analysis": {"weight": 0.25, "bad_actors_penalty": 0.8}
        }
    
    async def calculate_risk(self, transaction: TransactionData) -> float:
        """
        Calcula score de risco para uma transação
        
        Args:
            transaction: Dados da transação
            
        Returns:
            Score de risco (0.0 a 1.0)
        """
        try:
            # Calcular fatores individuais de risco
            factors = await self._calculate_risk_factors(transaction)
            
            # Combinar fatores com pesos
            weighted_score = 0.0
            total_weight = 0.0
            
            for factor in factors:
                weighted_score += factor.score * factor.weight
                total_weight += factor.weight
            
            # Normalizar score
            if total_weight > 0:
                final_score = weighted_score / total_weight
            else:
                final_score = 0.0
            
            # Aplicar ajustes finais
            final_score = self._apply_final_adjustments(final_score, transaction, factors)
            
            # Garantir que está no range [0.0, 1.0]
            final_score = max(0.0, min(1.0, final_score))
            
            logger.debug(f"Risk score calculated: {final_score:.3f} for tx {transaction.hash[:10]}...")
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.0  # Score seguro em caso de erro
    
    async def _calculate_risk_factors(self, transaction: TransactionData) -> List[RiskFactor]:
        """Calcula fatores individuais de risco"""
        factors = []
        
        # 1. Fator: Idade da carteira
        wallet_age_factor = await self._calculate_wallet_age_factor(transaction)
        factors.append(wallet_age_factor)
        
        # 2. Fator: Frequência de transações
        frequency_factor = await self._calculate_frequency_factor(transaction)
        factors.append(frequency_factor)
        
        # 3. Fator: Padrões de valor
        value_factor = await self._calculate_value_pattern_factor(transaction)
        factors.append(value_factor)
        
        # 4. Fator: Padrões temporais
        time_factor = await self._calculate_time_pattern_factor(transaction)
        factors.append(time_factor)
        
        # 5. Fator: Análise de rede
        network_factor = await self._calculate_network_factor(transaction)
        factors.append(network_factor)
        
        return factors
    
    async def _calculate_wallet_age_factor(self, transaction: TransactionData) -> RiskFactor:
        """Calcula fator de risco baseado na idade da carteira"""
        config = self.scoring_config["wallet_age"]
        
        # Simular idade da carteira (seria consulta real ao blockchain)
        wallet_age_hours = await self._get_wallet_age(transaction.from_address)
        threshold_hours = config["new_threshold_hours"]
        
        # Score mais alto para carteiras mais novas
        if wallet_age_hours < threshold_hours:
            # Score inversamente proporcional à idade
            age_score = 1.0 - (wallet_age_hours / threshold_hours)
            age_score = max(0.1, age_score)  # Mínimo de 0.1
        else:
            age_score = 0.1  # Score baixo para carteiras antigas
        
        return RiskFactor(
            name="wallet_age",
            score=age_score,
            weight=config["weight"],
            description=f"Wallet age: {wallet_age_hours:.1f} hours",
            evidence={
                "wallet_age_hours": wallet_age_hours,
                "threshold_hours": threshold_hours,
                "is_new_wallet": wallet_age_hours < threshold_hours
            }
        )
    
    async def _calculate_frequency_factor(self, transaction: TransactionData) -> RiskFactor:
        """Calcula fator de risco baseado na frequência de transações"""
        config = self.scoring_config["transaction_frequency"]
        
        # Simular frequência de transações (seria consulta ao histórico real)
        daily_tx_count = await self._get_daily_transaction_count(transaction.from_address)
        normal_range = config["normal_range"]
        
        # Score baseado no desvio da faixa normal
        if normal_range[0] <= daily_tx_count <= normal_range[1]:
            frequency_score = 0.1  # Frequência normal
        else:
            # Quanto mais fora da faixa normal, maior o score
            if daily_tx_count < normal_range[0]:
                deviation = (normal_range[0] - daily_tx_count) / normal_range[0]
            else:
                deviation = (daily_tx_count - normal_range[1]) / normal_range[1]
            
            frequency_score = min(0.8, 0.1 + deviation * 0.7)
        
        return RiskFactor(
            name="transaction_frequency",
            score=frequency_score,
            weight=config["weight"],
            description=f"Daily transaction count: {daily_tx_count}",
            evidence={
                "daily_count": daily_tx_count,
                "normal_range": normal_range,
                "is_abnormal": not (normal_range[0] <= daily_tx_count <= normal_range[1])
            }
        )
    
    async def _calculate_value_pattern_factor(self, transaction: TransactionData) -> RiskFactor:
        """Calcula fator de risco baseado em padrões de valor"""
        config = self.scoring_config["value_patterns"]
        
        value_score = 0.1  # Score base
        evidence = {}
        
        # 1. Verificar valores "redondos" suspeitos
        if self._is_round_number(transaction.value):
            value_score += config["round_number_penalty"]
            evidence["is_round_number"] = True
        
        # 2. Verificar valores próximos a limites regulatórios
        regulatory_limits = [10000, 50000, 100000]  # Limites comuns em USD
        for limit in regulatory_limits:
            if abs(transaction.value - limit) < limit * 0.05:  # 5% de proximidade
                value_score += 0.2
                evidence["near_regulatory_limit"] = limit
                break
        
        # 3. Verificar valores muito altos ou muito baixos
        if transaction.value > 1000000:  # > 1M USD
            value_score += 0.3
            evidence["very_high_value"] = True
        elif transaction.value < 1:  # < 1 USD
            value_score += 0.1
            evidence["very_low_value"] = True
        
        value_score = min(0.9, value_score)  # Máximo de 0.9
        
        return RiskFactor(
            name="value_patterns",
            score=value_score,
            weight=config["weight"],
            description=f"Transaction value: ${transaction.value:,.2f}",
            evidence=evidence
        )
    
    async def _calculate_time_pattern_factor(self, transaction: TransactionData) -> RiskFactor:
        """Calcula fator de risco baseado em padrões temporais"""
        config = self.scoring_config["time_patterns"]
        
        time_score = 0.1  # Score base
        evidence = {}
        
        tx_hour = transaction.timestamp.hour
        tx_weekday = transaction.timestamp.weekday()
        
        # 1. Verificar horários suspeitos (muito tarde/muito cedo)
        if tx_hour < 6 or tx_hour > 22:  # Entre 22h e 6h
            time_score += config["off_hours_penalty"]
            evidence["off_hours"] = True
        
        # 2. Verificar finais de semana para transações institucionais
        if tx_weekday >= 5:  # Sábado (5) ou Domingo (6)
            time_score += 0.1
            evidence["weekend_transaction"] = True
        
        # 3. Verificar feriados (implementação simplificada)
        if self._is_holiday(transaction.timestamp):
            time_score += 0.15
            evidence["holiday_transaction"] = True
        
        time_score = min(0.7, time_score)  # Máximo de 0.7
        
        return RiskFactor(
            name="time_patterns",
            score=time_score,
            weight=config["weight"],
            description=f"Transaction time: {transaction.timestamp.strftime('%Y-%m-%d %H:%M')}",
            evidence=evidence
        )
    
    async def _calculate_network_factor(self, transaction: TransactionData) -> RiskFactor:
        """Calcula fator de risco baseado na análise de rede"""
        config = self.scoring_config["network_analysis"]
        
        network_score = 0.1  # Score base
        evidence = {}
        
        # 1. Verificar interação com endereços conhecidos maliciosos
        is_from_bad = await self._is_known_bad_actor(transaction.from_address)
        is_to_bad = await self._is_known_bad_actor(transaction.to_address or "")
        
        if is_from_bad or is_to_bad:
            network_score += config["bad_actors_penalty"]
            evidence["bad_actor_interaction"] = True
        
        # 2. Verificar interação com exchanges suspeitas
        if await self._is_suspicious_exchange(transaction.to_address or ""):
            network_score += 0.3
            evidence["suspicious_exchange"] = True
        
        # 3. Verificar padrões de mixer/tumbler
        if await self._is_mixer_pattern(transaction):
            network_score += 0.4
            evidence["mixer_pattern"] = True
        
        network_score = min(0.9, network_score)  # Máximo de 0.9
        
        return RiskFactor(
            name="network_analysis",
            score=network_score,
            weight=config["weight"],
            description="Network relationship analysis",
            evidence=evidence
        )
    
    def _apply_final_adjustments(
        self, 
        base_score: float, 
        transaction: TransactionData, 
        factors: List[RiskFactor]
    ) -> float:
        """Aplica ajustes finais ao score de risco"""
        adjusted_score = base_score
        
        # 1. Boost para combinações específicas de fatores de risco
        high_risk_factors = [f for f in factors if f.score > 0.7]
        if len(high_risk_factors) >= 2:
            adjusted_score += 0.1  # Boost por múltiplos fatores de alto risco
        
        # 2. Penalidade extra para transações muito suspeitas
        if transaction.transaction_type == TransactionType.CONTRACT_INTERACTION:
            adjusted_score += 0.05  # Interações com contratos são ligeiramente mais arriscadas
        
        # 3. Ajuste baseado na confiança geral
        confidence_factors = [f.score * f.weight for f in factors]
        if confidence_factors:
            confidence = sum(confidence_factors) / len(confidence_factors)
            if confidence < 0.3:
                adjusted_score *= 0.8  # Reduz score se confiança é baixa
        
        return adjusted_score
    
    # Métodos auxiliares (implementações simplificadas)
    
    async def _get_wallet_age(self, address: str) -> float:
        """Obtém idade da carteira em horas"""
        # Implementação simulada
        return 72.0  # 3 dias
    
    async def _get_daily_transaction_count(self, address: str) -> int:
        """Obtém contagem diária de transações"""
        # Implementação simulada
        return 5
    
    def _is_round_number(self, value: float) -> bool:
        """Verifica se é um número "redondo" suspeito"""
        # Verificar se é múltiplo de potências de 10
        for power in range(1, 6):  # 10, 100, 1000, 10000, 100000
            threshold = 10 ** power
            if abs(value % threshold) < threshold * 0.01:  # 1% de tolerância
                return True
        return False
    
    def _is_holiday(self, timestamp: datetime) -> bool:
        """Verifica se é feriado (implementação simplificada)"""
        # Implementação muito básica - seria integração com calendário real
        return False
    
    async def _is_known_bad_actor(self, address: str) -> bool:
        """Verifica se endereço é conhecido como malicioso"""
        # Lista simulada de endereços maliciosos
        bad_actors = {
            "0x1234567890abcdef1234567890abcdef12345678",
            "0xabcdef1234567890abcdef1234567890abcdef12"
        }
        return address.lower() in {addr.lower() for addr in bad_actors}
    
    async def _is_suspicious_exchange(self, address: str) -> bool:
        """Verifica se é exchange suspeita"""
        # Implementação simulada
        return False
    
    async def _is_mixer_pattern(self, transaction: TransactionData) -> bool:
        """Detecta padrões de mixing/tumbling"""
        # Implementação simplificada - verificaria padrões complexos
        return False
    
    def get_risk_breakdown(self, transaction: TransactionData) -> Dict[str, Any]:
        """Retorna breakdown detalhado do risco para análise"""
        # Implementação futura para debugging e transparência
        return {
            "transaction_hash": transaction.hash,
            "timestamp": transaction.timestamp.isoformat(),
            "factors": [],  # Lista detalhada de fatores
            "final_score": 0.0,
            "risk_level": "LOW"
        }
    
    async def get_risk_factors(self, transaction: TransactionData) -> Dict[str, Any]:
        """Get detailed risk factors for a transaction - implementing IRiskScorer interface"""
        try:
            factors = await self._calculate_risk_factors(transaction)
            
            result = {
                "transaction_hash": transaction.hash,
                "timestamp": transaction.timestamp.isoformat(),
                "factors": {}
            }
            
            for factor in factors:
                result["factors"][factor.name] = {
                    "score": factor.score,
                    "weight": factor.weight,
                    "description": factor.description,
                    "evidence": factor.evidence
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting risk factors: {e}")
            return {
                "transaction_hash": transaction.hash,
                "error": str(e),
                "factors": {}
            }
