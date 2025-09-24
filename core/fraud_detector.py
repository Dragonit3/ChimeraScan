"""
Motor Principal de Detecção de Fraudes
Implementa os princípios de Separation of Concerns e Performance
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

from config.settings import settings
from data.models import TransactionData, AlertData, RiskLevel, TransactionType, DetectionResult
from data.simple_database import SimpleDatabase
from interfaces.fraud_detection import IRuleEngine, IRiskScorer, IFraudDetector

logger = logging.getLogger(__name__)

class FraudDetector(IFraudDetector):
    """
    Motor principal de detecção de fraudes
    
    Responsabilidades:
    - Coordenar análise de transações
    - Aplicar regras de detecção
    - Calcular scores de risco
    - Gerar alertas quando necessário
    """
    
    def __init__(self, rule_engine: Optional[IRuleEngine] = None, risk_scorer: Optional[IRiskScorer] = None):
        # Use dependency injection if provided, otherwise create defaults
        if rule_engine is None:
            from core.rule_engine import RuleEngine
            self.rule_engine = RuleEngine()
        else:
            self.rule_engine = rule_engine
            
        if risk_scorer is None:
            from core.risk_scorer import RiskScorer
            self.risk_scorer = RiskScorer()
        else:
            self.risk_scorer = risk_scorer
            
        # Inicializar banco de dados simples
        self.db = SimpleDatabase()
        
        # Carregar estatísticas do banco ao inicializar
        self._load_stats_from_database()
        
        # Tracking de volume por período (para gráficos em tempo real)
        self._transaction_history = []  # Lista de timestamps das últimas transações
        self._last_volume_check = datetime.utcnow()
        
        # Cache para otimização de performance
        self._wallet_cache = {}
        self._pattern_cache = {}
        
        logger.info("FraudDetector initialized successfully with database persistence")
    
    def _load_stats_from_database(self):
        """Carrega estatísticas do banco de dados ao inicializar"""
        try:
            db_stats = self.db.get_statistics()
            
            self.detection_stats = {
                "total_analyzed": db_stats.get("total_analyzed", 0),
                "suspicious_detected": db_stats.get("suspicious_detected", 0),
                "alerts_generated": db_stats.get("alerts_generated", 0),
                "total_risk_score": db_stats.get("total_risk_score", 0.0),
                "last_reset": datetime.utcnow()  # Reset timer to now
            }
            
            logger.info(f"Loaded stats from database: {self.detection_stats}")
            
        except Exception as e:
            logger.error(f"Error loading stats from database: {e}")
            # Fallback to empty stats
            self.detection_stats = {
                "total_analyzed": 0,
                "suspicious_detected": 0,
                "alerts_generated": 0,
                "total_risk_score": 0.0,
                "last_reset": datetime.utcnow()
            }
    
    async def analyze_transaction(self, transaction: TransactionData) -> DetectionResult:
        """
        Analisa uma transação em busca de padrões fraudulentos
        
        Args:
            transaction: Dados da transação para análise
            
        Returns:
            DetectionResult com resultado da análise
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. Aplicar regras de detecção
            rule_results = await self.rule_engine.evaluate_transaction(transaction)
            
            # 2. Calcular score de risco
            risk_score = await self.risk_scorer.calculate_risk(transaction)
            
            # 3. Determinar nível de risco
            risk_level = self._determine_risk_level(risk_score)
            
            # 4. Verificar se é suspeito
            # CORREÇÃO: Se há alertas gerados, então é suspeito
            is_suspicious = risk_score >= settings.detection.anomaly_detection_threshold
            
            # 5. Gerar alertas se necessário
            alerts = []
            triggered_rules = []
            
            for rule_result in rule_results:
                if rule_result.triggered:
                    triggered_rules.append(rule_result.rule_name)
                    
                    if rule_result.generate_alert:
                        # Enriquecer contexto do alerta com dados da transação
                        enriched_context = {
                            **rule_result.context,
                            # Dados da transação original
                            "transaction_value": transaction.value,
                            "from_address": transaction.from_address,
                            "to_address": transaction.to_address,
                            "gas_price": transaction.gas_price,
                            "block_number": transaction.block_number,
                            "timestamp": transaction.timestamp.isoformat(),
                            # Dados de funding se disponíveis
                            "fundeddate_from": transaction.fundeddate_from.isoformat() if transaction.fundeddate_from else None,
                            "fundeddate_to": transaction.fundeddate_to.isoformat() if transaction.fundeddate_to else None,
                            "has_real_funding_data": transaction.fundeddate_from is not None or transaction.fundeddate_to is not None
                        }
                        
                        alert = AlertData(
                            rule_name=rule_result.rule_name,
                            severity=rule_result.severity,
                            transaction_hash=transaction.hash,
                            title=rule_result.alert_title,
                            description=rule_result.alert_description,
                            risk_score=risk_score,
                            wallet_address=transaction.from_address,
                            context_data=enriched_context
                        )
                        alerts.append(alert)
            
            # CORREÇÃO: Recalcular se é suspeito baseado nos alertas gerados
            is_suspicious = len(alerts) > 0 or risk_score >= settings.detection.anomaly_detection_threshold
            
            # 6. Compilar contexto adicional
            context = {
                "analysis_duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "rules_evaluated": len(rule_results),
                "wallet_age_hours": await self._get_wallet_age(transaction.from_address),
                "gas_price_ratio": transaction.gas_price / await self._get_average_gas_price(),
                "transaction_type": transaction.transaction_type.value
            }
            
            # 7. Atualizar estatísticas
            self._update_stats(is_suspicious, len(alerts), risk_score)
            
            result = DetectionResult(
                is_suspicious=is_suspicious,
                risk_score=risk_score,
                risk_level=risk_level,
                triggered_rules=triggered_rules,
                alerts=alerts,
                context=context
            )
            
            # 8. Salvar no banco de dados
            try:
                # Converter para formato simples
                transaction_dict = {
                    'hash': transaction.hash,
                    'from_address': transaction.from_address,
                    'to_address': transaction.to_address,
                    'value': transaction.value,
                    'gas_price': transaction.gas_price,
                    'block_number': transaction.block_number,
                    'timestamp': transaction.timestamp.isoformat()
                }
                
                analysis_dict = {
                    'is_suspicious': is_suspicious,
                    'risk_score': risk_score,
                    'triggered_rules': triggered_rules
                }
                
                # Salvar transação
                self.db.save_transaction(transaction_dict, analysis_dict)
                
                # Não persiste alertas aqui - isso é responsabilidade do AlertManager
                # Os alertas serão persistidos quando processados pelo AlertManager
                
                logger.debug(f"Transaction persisted to database: {transaction.hash}")
                
            except Exception as db_error:
                logger.error(f"Error persisting to database: {db_error}")
                # Não falha a análise se o banco falhar
            
            logger.info(
                f"Transaction analyzed: {transaction.hash[:10]}... "
                f"Risk: {risk_score:.3f} ({risk_level.value}) "
                f"Suspicious: {is_suspicious} "
                f"Alerts: {len(alerts)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing transaction {transaction.hash}: {str(e)}")
            # Retorna resultado seguro em caso de erro
            return DetectionResult(
                is_suspicious=False,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                triggered_rules=[],
                alerts=[],
                context={"error": str(e)}
            )
    
    async def analyze_batch(self, transactions: List[TransactionData]) -> List[DetectionResult]:
        """
        Analisa um lote de transações de forma eficiente
        
        Args:
            transactions: Lista de transações para análise
            
        Returns:
            Lista de resultados de detecção
        """
        if not transactions:
            return []
        
        logger.info(f"Starting batch analysis of {len(transactions)} transactions")
        
        # Análise assíncrona para melhor performance
        tasks = [self.analyze_transaction(tx) for tx in transactions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar exceções e retornar apenas resultados válidos
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in batch analysis for transaction {i}: {result}")
                # Criar resultado padrão para transação com erro
                valid_results.append(DetectionResult(
                    is_suspicious=False,
                    risk_score=0.0,
                    risk_level=RiskLevel.LOW,
                    triggered_rules=[],
                    alerts=[],
                    context={"batch_error": str(result)}
                ))
            else:
                valid_results.append(result)
        
        logger.info(f"Batch analysis completed: {len(valid_results)} results")
        return valid_results
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determina o nível de risco baseado no score"""
        if risk_score >= 0.95:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.8:
            return RiskLevel.HIGH
        elif risk_score >= 0.6:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _get_wallet_age(self, address: str) -> float:
        """Obtém a idade da carteira em horas (com cache e consulta real)"""
        # Verificar cache primeiro
        if address in self._wallet_cache:
            cached_data = self._wallet_cache[address]
            # Cache válido por 1 hora
            if (datetime.utcnow() - cached_data["cached_at"]).total_seconds() < 3600:
                return cached_data["age_hours"]
        
        try:
            # Tentar obter idade real via Etherscan API
            import os
            import requests
            etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
            
            if etherscan_api_key:
                logger.info(f"Consultando idade real da carteira {address[:10]}...")
                
                # Buscar primeira transação do endereço
                url = "https://api.etherscan.io/api"
                params = {
                    "module": "account",
                    "action": "txlist",
                    "address": address,
                    "startblock": "0",
                    "endblock": "99999999",
                    "page": "1",
                    "offset": "1",
                    "sort": "asc",
                    "apikey": etherscan_api_key
                }
                
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1" and data.get("result"):
                        # Primeira transação encontrada
                        first_tx = data["result"][0]
                        first_timestamp = int(first_tx["timeStamp"])
                        first_date = datetime.fromtimestamp(first_timestamp)
                        
                        # Calcular idade em horas
                        age_hours = (datetime.utcnow() - first_date).total_seconds() / 3600
                        
                        # Cache do resultado
                        self._wallet_cache[address] = {
                            "age_hours": age_hours,
                            "first_tx_date": first_date.isoformat(),
                            "first_tx_hash": first_tx["hash"],
                            "method": "etherscan_api",
                            "cached_at": datetime.utcnow()
                        }
                        
                        logger.info(f"✅ Carteira {address[:10]}... idade: {age_hours:.1f}h (primeira tx: {first_date.strftime('%Y-%m-%d %H:%M')})")
                        return age_hours
                    else:
                        logger.warning(f"Etherscan API não retornou transações para {address[:10]}...")
                else:
                    logger.warning(f"Etherscan API retornou status {response.status_code}")
        
        except Exception as e:
            logger.warning(f"Falha ao obter idade real da carteira {address[:10]}...: {e}")
        
        # Fallback para valor simulado se API falhar
        age_hours = 168.0  # 1 semana como padrão
        
        self._wallet_cache[address] = {
            "age_hours": age_hours,
            "method": "simulated_fallback",
            "cached_at": datetime.utcnow()
        }
        
        logger.info(f"⚠️ Usando idade simulada para {address[:10]}...: {age_hours}h")
        return age_hours
    
    async def _get_average_gas_price(self) -> float:
        """Obtém o preço médio de gas atual da configuração"""
        try:
            # Carregar configuração das regras
            import json
            with open('config/rules.json', 'r') as f:
                rules_config = json.load(f)
            base_gas_price = rules_config["institutional_rules"]["suspicious_gas_price"].get("base_gas_price", 25.0)
            return base_gas_price
        except:
            # Fallback se não conseguir carregar configuração
            return 25.0
    
    def _update_stats(self, is_suspicious: bool, alert_count: int, risk_score: float):
        """Atualiza estatísticas de detecção"""
        now = datetime.utcnow()
        
        # Registrar timestamp da transação para volume
        self._transaction_history.append(now)
        
        # Limpar histórico antigo (manter apenas últimos 5 minutos)
        cutoff_time = now - timedelta(minutes=5)
        self._transaction_history = [t for t in self._transaction_history if t > cutoff_time]
        
        self.detection_stats["total_analyzed"] += 1
        self.detection_stats["total_risk_score"] += risk_score
        
        if is_suspicious:
            self.detection_stats["suspicious_detected"] += 1
        
        self.detection_stats["alerts_generated"] += alert_count
    
    def get_recent_volume(self, seconds: int = 10) -> int:
        """Retorna número de transações processadas nos últimos X segundos"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=seconds)
        
        # Contar transações no período
        recent_count = sum(1 for t in self._transaction_history if t > cutoff_time)
        return recent_count
    
    def get_stats(self) -> Dict[str, any]:
        """Retorna estatísticas de detecção"""
        stats = self.detection_stats.copy()
        
        # Calcular métricas derivadas
        total = stats["total_analyzed"]
        if total > 0:
            stats["suspicious_rate"] = stats["suspicious_detected"] / total
            stats["alert_rate"] = stats["alerts_generated"] / total
            stats["average_risk_score"] = stats["total_risk_score"] / total
        else:
            stats["suspicious_rate"] = 0.0
            stats["alert_rate"] = 0.0
            stats["average_risk_score"] = 0.0
        
        stats["uptime_hours"] = (
            datetime.utcnow() - stats["last_reset"]
        ).total_seconds() / 3600
        
        return stats
    
    def reset_stats(self):
        """Reseta estatísticas de detecção"""
        self.detection_stats = {
            "total_analyzed": 0,
            "suspicious_detected": 0,
            "alerts_generated": 0,
            "total_risk_score": 0.0,
            "last_reset": datetime.utcnow()
        }
        logger.info("Detection statistics reset")
    
    def clear_cache(self):
        """Limpa caches para otimização de memória"""
        cache_size_before = len(self._wallet_cache) + len(self._pattern_cache)
        
        # Remove entradas antigas do cache (> 1 hora)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        self._wallet_cache = {
            k: v for k, v in self._wallet_cache.items()
            if v.get("cached_at", datetime.min) > cutoff_time
        }
        
        self._pattern_cache = {
            k: v for k, v in self._pattern_cache.items()
            if v.get("cached_at", datetime.min) > cutoff_time
        }
        
        cache_size_after = len(self._wallet_cache) + len(self._pattern_cache)
        
        logger.info(
            f"Cache cleared: {cache_size_before} -> {cache_size_after} entries"
        )
