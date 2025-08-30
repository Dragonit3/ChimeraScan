"""
Engine de Regras Customizáveis para Detecção de Fraudes
Implementa o princípio de Adaptabilidade e Escalabilidade
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from config.settings import settings
from data.models import TransactionData, RiskLevel, TransactionType
from interfaces.fraud_detection import IRuleEngine

logger = logging.getLogger(__name__)

@dataclass
class RuleResult:
    """Resultado da avaliação de uma regra"""
    rule_name: str
    triggered: bool
    severity: RiskLevel
    confidence: float
    alert_title: str
    alert_description: str
    context: Dict[str, Any]
    generate_alert: bool = False

class RuleEngine(IRuleEngine):
    """
    Engine de regras para detecção de fraudes
    
    Permite configuração dinâmica de regras através do arquivo rules.json
    Implementa padrões de fraude conhecidos e customizáveis
    """
    
    def __init__(self):
        self.rules_config = self._load_rules_config()
        self.active_rules = self._initialize_rules()
        logger.info(f"RuleEngine initialized with {len(self.active_rules)} active rules")
    
    def _load_rules_config(self) -> Dict[str, Any]:
        """Carrega configuração de regras do arquivo JSON"""
        try:
            with open("config/rules.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("rules.json not found, using default rules")
            return self._get_default_rules()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing rules.json: {e}")
            return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Retorna regras padrão caso não consiga carregar do arquivo"""
        return {
            "institutional_rules": {
                "high_value_transfer": {
                    "enabled": True,
                    "threshold_usd": 100000,
                    "severity": "HIGH",
                    "description": "High value transfer detected",
                    "action": "immediate_alert"
                }
            }
        }
    
    def _initialize_rules(self) -> List[str]:
        """Inicializa lista de regras ativas"""
        active_rules = []
        institutional_rules = self.rules_config.get("institutional_rules", {})
        
        for rule_name, rule_config in institutional_rules.items():
            if rule_config.get("enabled", False):
                active_rules.append(rule_name)
        
        return active_rules
    
    async def evaluate_transaction(self, transaction: TransactionData) -> List[RuleResult]:
        """
        Avalia uma transação contra todas as regras ativas
        
        Args:
            transaction: Dados da transação para avaliar
            
        Returns:
            Lista de resultados de regras
        """
        results = []
        
        for rule_name in self.active_rules:
            try:
                result = await self._evaluate_rule(rule_name, transaction)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_name}: {e}")
        
        return results
    
    async def _evaluate_rule(self, rule_name: str, transaction: TransactionData) -> Optional[RuleResult]:
        """Avalia uma regra específica"""
        
        # Dispatch para método específico da regra
        rule_method = getattr(self, f"_rule_{rule_name}", None)
        if rule_method:
            return await rule_method(transaction)
        else:
            logger.warning(f"Rule method not found: _rule_{rule_name}")
            return None
    
    async def _rule_high_value_transfer(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Transferência de alto valor"""
        rule_config = self.rules_config["institutional_rules"]["high_value_transfer"]
        threshold = rule_config["threshold_usd"]
        
        if transaction.value >= threshold:
            return RuleResult(
                rule_name="high_value_transfer",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.9,
                alert_title=f"High Value Transfer: ${transaction.value:,.2f}",
                alert_description=f"Transfer of ${transaction.value:,.2f} exceeds threshold of ${threshold:,.2f}",
                context={
                    "transaction_value": transaction.value,
                    "threshold": threshold,
                    "ratio": transaction.value / threshold
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_new_wallet_interaction(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Interação com carteira nova"""
        rule_config = self.rules_config["institutional_rules"]["new_wallet_interaction"]
        
        # Verificar ambas as carteiras: from_address e to_address
        from_age_hours = await self._get_wallet_age_for_address(transaction.from_address, transaction, "from")
        to_age_hours = await self._get_wallet_age_for_address(transaction.to_address, transaction, "to") if transaction.to_address else None
        
        threshold_hours = rule_config["wallet_age_hours"]
        min_value = rule_config["min_value_usd"]
        
        # Verificar se alguma das carteiras é nova e o valor é suficiente
        new_wallet_detected = False
        youngest_age = None
        wallet_type = None
        
        if from_age_hours < threshold_hours and transaction.value >= min_value:
            new_wallet_detected = True
            youngest_age = from_age_hours
            wallet_type = "from_address"
        
        if to_age_hours is not None and to_age_hours < threshold_hours and transaction.value >= min_value:
            if not new_wallet_detected or to_age_hours < youngest_age:
                new_wallet_detected = True
                youngest_age = to_age_hours
                wallet_type = "to_address"
        
        if new_wallet_detected:
            return RuleResult(
                rule_name="new_wallet_interaction",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.7,
                alert_title=f"New Wallet Interaction: {youngest_age:.1f}h old ({wallet_type})",
                alert_description=f"Transaction with {wallet_type} wallet created {youngest_age:.1f} hours ago",
                context={
                    "wallet_age_hours": youngest_age,
                    "wallet_type": wallet_type,
                    "from_age_hours": from_age_hours,
                    "to_age_hours": to_age_hours,
                    "threshold_hours": threshold_hours,
                    "transaction_value": transaction.value,
                    "used_fundeddate": transaction.fundeddate_from is not None or transaction.fundeddate_to is not None
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_wash_trading_pattern(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Padrão de wash trading"""
        rule_config = self.rules_config["institutional_rules"]["wash_trading_pattern"]
        
        # Verificar padrões de wash trading
        is_wash_trading = await self._detect_wash_trading(transaction, rule_config)
        
        if is_wash_trading:
            return RuleResult(
                rule_name="wash_trading_pattern",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.85,
                alert_title="Potential Wash Trading Detected",
                alert_description="Pattern consistent with wash trading behavior",
                context={
                    "pattern_type": "wash_trading",
                    "time_window": rule_config["time_window_minutes"]
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_blacklist_interaction(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Interação com endereço na lista negra"""
        rule_config = self.rules_config["institutional_rules"]["blacklist_interaction"]
        
        # Verificar se algum endereço está na lista negra
        addresses_to_check = [transaction.from_address]
        if transaction.to_address:
            addresses_to_check.append(transaction.to_address)
        
        blacklisted_addresses = []
        
        for address in addresses_to_check:
            if await self._is_blacklisted(address):
                interaction_type = "from" if address == transaction.from_address else "to"
                blacklisted_addresses.append({
                    "address": address,
                    "interaction_type": interaction_type
                })
        
        # Se encontrou endereços blacklistados, criar alerta
        if blacklisted_addresses:
            # Determinar título e descrição baseado na quantidade
            if len(blacklisted_addresses) == 1:
                addr = blacklisted_addresses[0]
                title = "Blacklisted Address Interaction"
                description = f"Transaction involves blacklisted address: {addr['address']} ({addr['interaction_type']})"
                primary_address = addr["address"]
            else:
                addresses_str = ", ".join([f"{addr['address']} ({addr['interaction_type']})" for addr in blacklisted_addresses])
                title = "Multiple Blacklisted Addresses Interaction"
                description = f"Transaction involves multiple blacklisted addresses: {addresses_str}"
                primary_address = blacklisted_addresses[0]["address"]  # Usar primeiro para compatibilidade
            
            return RuleResult(
                rule_name="blacklist_interaction",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=1.0,
                alert_title=title,
                alert_description=description,
                context={
                    "blacklisted_addresses": blacklisted_addresses,
                    "blacklisted_address": primary_address,  # Manter compatibilidade
                    "interaction_type": blacklisted_addresses[0]["interaction_type"],  # Manter compatibilidade
                    "multiple_addresses": len(blacklisted_addresses) > 1,
                    "total_blacklisted": len(blacklisted_addresses)
                },
                generate_alert=True  # Sempre gera alerta para lista negra
            )
        
        return None
    
    async def _rule_suspicious_gas_price(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Preço de gas suspeito"""
        rule_config = self.rules_config["institutional_rules"]["suspicious_gas_price"]
        
        # Obter preço médio de gas
        avg_gas_price = await self._get_average_gas_price()
        multiplier = rule_config["multiplier"]
        
        # Verificar se gas price é muito alto ou muito baixo
        is_suspicious = (
            transaction.gas_price > avg_gas_price * multiplier or
            transaction.gas_price < avg_gas_price / multiplier
        )
        
        if is_suspicious:
            ratio = transaction.gas_price / avg_gas_price
            return RuleResult(
                rule_name="suspicious_gas_price",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.6,
                alert_title=f"Suspicious Gas Price: {ratio:.1f}x average",
                alert_description=f"Gas price {ratio:.1f}x the current average",
                context={
                    "transaction_gas_price": transaction.gas_price,
                    "average_gas_price": avg_gas_price,
                    "ratio": ratio
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_multiple_small_transfers(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Múltiplas transferências pequenas (possível evasão)"""
        rule_config = self.rules_config["institutional_rules"]["multiple_small_transfers"]
        
        # Verificar padrão de múltiplas transferências pequenas
        pattern_detected = await self._detect_structuring_pattern(transaction, rule_config)
        
        if pattern_detected:
            return RuleResult(
                rule_name="multiple_small_transfers",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.75,
                alert_title="Potential Structuring Detected",
                alert_description="Multiple small transfers may indicate structuring/smurfing",
                context={
                    "pattern_type": "structuring",
                    "individual_value": transaction.value,
                    "threshold": rule_config["max_individual_value_usd"]
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_unusual_time_pattern(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Transação em horário incomum"""
        rule_config = self.rules_config["institutional_rules"]["unusual_time_pattern"]
        
        # Extrair horário da transação
        transaction_time = transaction.timestamp
        hour = transaction_time.hour
        is_weekend = transaction_time.weekday() >= 5  # 5=Saturday, 6=Sunday
        
        # Verificar se está no horário suspeito (22:00-06:00)
        is_off_hours = hour >= 22 or hour <= 6
        min_value = rule_config["min_value_usd"]
        
        # Aplicar regra
        is_suspicious = False
        if transaction.value >= min_value:
            if is_off_hours:
                is_suspicious = True
            elif is_weekend and rule_config["weekend_enabled"]:
                is_suspicious = True
        
        if is_suspicious:
            context_info = "off hours" if is_off_hours else "weekend"
            return RuleResult(
                rule_name="unusual_time_pattern",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.6,
                alert_title=f"Unusual Time Pattern: Transaction at {context_info}",
                alert_description=f"High value transaction (${transaction.value:,.2f}) during {context_info}",
                context={
                    "transaction_hour": hour,
                    "is_weekend": is_weekend,
                    "is_off_hours": is_off_hours,
                    "transaction_value": transaction.value
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    async def _rule_token_swap_anomaly(self, transaction: TransactionData) -> Optional[RuleResult]:
        """Regra: Anomalia em swap de tokens"""
        rule_config = self.rules_config["institutional_rules"]["token_swap_anomaly"]
        
        # Verificar se é transação de token
        if not transaction.token_address:
            return None
        
        # Simular verificação de anomalias de preço e volume
        # Em implementação real, consultaria APIs de DEX e dados de mercado
        price_deviation = await self._get_token_price_deviation(transaction.token_address)
        volume_spike = await self._get_volume_spike_factor(transaction.token_address)
        
        price_threshold = rule_config["price_deviation_threshold"]
        volume_threshold = rule_config["volume_spike_multiplier"]
        
        if price_deviation > price_threshold or volume_spike > volume_threshold:
            return RuleResult(
                rule_name="token_swap_anomaly",
                triggered=True,
                severity=RiskLevel(rule_config["severity"]),
                confidence=0.8,
                alert_title=f"Token Swap Anomaly: {transaction.token_address[:10]}...",
                alert_description=f"Unusual price deviation ({price_deviation:.2%}) or volume spike ({volume_spike:.1f}x)",
                context={
                    "token_address": transaction.token_address,
                    "price_deviation": price_deviation,
                    "volume_spike": volume_spike,
                    "price_threshold": price_threshold,
                    "volume_threshold": volume_threshold
                },
                generate_alert=rule_config["action"] == "immediate_alert"
            )
        
        return None
    
    # Métodos auxiliares (implementações simplificadas)
    
    async def _get_wallet_age_for_address(self, address: str, transaction: Optional[TransactionData] = None, wallet_type: str = "unknown") -> float:
        """
        Obtém idade da carteira específica em horas
        
        Args:
            address: Endereço da carteira
            transaction: Dados da transação (opcional, para usar fundeddate_from/to)
            wallet_type: "from" ou "to" para determinar qual fundeddate usar
        
        Returns:
            Idade da carteira em horas
        """
        if not address:
            return 48.0  # Valor padrão se endereço não fornecido
            
        # Se as datas de funded foram fornecidas, usar elas para calcular a idade
        if transaction:
            current_time = transaction.timestamp
            funded_date = None
            
            # Usar a data correta baseada no tipo de carteira
            if wallet_type == "from" and transaction.fundeddate_from:
                funded_date = transaction.fundeddate_from
            elif wallet_type == "to" and transaction.fundeddate_to:
                funded_date = transaction.fundeddate_to
            elif transaction.fundeddate_from or transaction.fundeddate_to:
                # Fallback: usar qualquer data disponível
                funded_date = transaction.fundeddate_from or transaction.fundeddate_to
            
            if funded_date:
                # Calcular idade em horas
                age_delta = current_time - funded_date
                wallet_age_hours = age_delta.total_seconds() / 3600.0
                
                # Garantir que seja positivo
                return max(0.0, wallet_age_hours)
        
        # Implementação simulada padrão - seria consulta real ao blockchain
        return 48.0  # 48 horas como padrão

    async def _get_wallet_age(self, address: str, transaction: Optional[TransactionData] = None) -> float:
        """
        Obtém idade da carteira em horas (método legado para compatibilidade)
        
        Args:
            address: Endereço da carteira
            transaction: Dados da transação (opcional, para usar fundeddate_from/to)
        
        Returns:
            Idade da carteira em horas
        """
        return await self._get_wallet_age_for_address(address, transaction)
    
    async def _get_average_gas_price(self) -> float:
        """Obtém preço médio atual de gas"""
        # Implementação simulada - seria consulta real à rede
        return 25.0  # 25 Gwei
    
    async def _is_blacklisted(self, address: str) -> bool:
        """
        Verifica se endereço está na lista negra usando banco de dados
        Fallback para lista hardcoded se banco não estiver disponível
        """
        try:
            # Tentar consulta no banco de dados primeiro
            from core.blacklist_manager import get_blacklist_database
            
            blacklist_db = get_blacklist_database()
            is_blacklisted = await blacklist_db.is_address_blacklisted(address)
            
            if is_blacklisted:
                # Log informações adicionais se encontrado
                blacklist_info = await blacklist_db.get_blacklist_info(address)
                if blacklist_info:
                    logger.info(f"Blacklist hit: {address} - {blacklist_info.severity_level.value} - {blacklist_info.reason}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Blacklist database unavailable, using fallback list: {e}")
            
            # Fallback para lista hardcoded se banco não estiver disponível
            blacklisted_addresses = {
                "0x1234567890abcdef1234567890abcdef12345678",  # Exemplo
            }
            
            return address.lower() in {addr.lower() for addr in blacklisted_addresses}
    
    async def _get_token_price_deviation(self, token_address: str) -> float:
        """
        Calcula desvio de preço do token em relação à média
        
        Retorna: float representando desvio percentual (0.1 = 10%)
        """
        # Implementação simulada - seria consulta real a APIs de DEX
        import random
        return random.uniform(0.02, 0.15)  # 2% a 15% de desvio simulado
    
    async def _get_volume_spike_factor(self, token_address: str) -> float:
        """
        Calcula fator de spike de volume do token
        
        Retorna: float representando multiplicador de volume (2.0 = 2x o volume normal)
        """
        # Implementação simulada - seria consulta real a dados de volume
        import random
        return random.uniform(0.5, 12.0)  # 0.5x a 12x o volume normal
    
    async def _get_transaction_pattern_history(self, address: str, window_minutes: int) -> List[Dict]:
        """
        Obtém histórico de transações para análise de padrões
        
        Args:
            address: Endereço para analisar
            window_minutes: Janela de tempo em minutos
            
        Returns:
            Lista de transações históricas simuladas
        """
        # Implementação simulada - seria consulta real ao banco de dados
        import random
        from datetime import datetime, timedelta
        
        now = datetime.now()
        transactions = []
        
        # Gerar 2-8 transações simuladas na janela de tempo
        num_transactions = random.randint(2, 8)
        for i in range(num_transactions):
            transactions.append({
                "timestamp": now - timedelta(minutes=random.randint(1, window_minutes)),
                "value": random.uniform(1000, 10000),
                "from_address": address,
                "hash": f"0x{random.randint(100000000000, 999999999999):012x}"
            })
        
        return transactions
    
    async def _detect_wash_trading(self, transaction: TransactionData, config: Dict) -> bool:
        """Detecta padrões de wash trading"""
        # Implementação simplificada - seria análise mais complexa
        # Verificaria histórico recente de transações entre mesmos endereços
        return False  # Placeholder
    
    async def _detect_structuring_pattern(self, transaction: TransactionData, config: Dict) -> bool:
        """Detecta padrões de estruturação (smurfing)"""
        # Implementação simplificada - verificaria múltiplas transações pequenas
        max_individual = config["max_individual_value_usd"]
        return transaction.value < max_individual and transaction.value > max_individual * 0.8
    
    def reload_rules(self):
        """Recarrega configuração de regras"""
        logger.info("Reloading rules configuration")
        self.rules_config = self._load_rules_config()
        self.active_rules = self._initialize_rules()
        logger.info(f"Rules reloaded: {len(self.active_rules)} active rules")
    
    def get_active_rules(self) -> List[str]:
        """Retorna lista de regras ativas que possuem implementação"""
        # Filtrar apenas regras que têm método implementado
        implementable_rules = []
        for rule_name in self.active_rules:
            if self._is_rule_implementable(rule_name):
                implementable_rules.append(rule_name)
            else:
                logger.debug(f"Rule '{rule_name}' is enabled but not implemented, skipping")
        
        return implementable_rules
    
    def _is_rule_implementable(self, rule_name: str) -> bool:
        """
        Verifica se uma regra possui implementação disponível
        
        Princípio: Single Responsibility - método dedicado à validação
        """
        method_name = f"_rule_{rule_name}"
        return hasattr(self, method_name) and callable(getattr(self, method_name))
    
    def get_all_configured_rules(self) -> List[str]:
        """
        Retorna todas as regras configuradas (independente de implementação)
        
        Princípio: Interface Segregation - método específico para diferentes necessidades
        """
        institutional_rules = self.rules_config.get("institutional_rules", {})
        return list(institutional_rules.keys())
    
    def get_rule_config(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """Retorna configuração de uma regra específica"""
        return self.rules_config.get("institutional_rules", {}).get(rule_name)
    
    def reload_rules(self) -> bool:
        """Reload rules configuration - implementing IRuleEngine interface"""
        try:
            self.rules_config = self._load_rules_config()
            self.active_rules = self._initialize_rules()
            logger.info(f"Rules reloaded successfully. {len(self.active_rules)} active rules.")
            return True
        except Exception as e:
            logger.error(f"Failed to reload rules: {e}")
            return False
    
    def get_active_rules(self) -> List[str]:
        """Get list of active rule names - implementing IRuleEngine interface"""
        return self.active_rules.copy()
