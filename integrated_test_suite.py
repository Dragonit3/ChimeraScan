#!/usr/bin/env python3
"""
Sistema Integrado de Testes para Detecção de Fraudes TecBan
Implementa princípios de Clean Architecture e SOLID
"""
import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv

from continuous_monitor import ContinuousMonitor, BlockchainProvider

load_dotenv()

# ========================================
# INFRASTRUCTURE LAYER - Serviços Externos
# ========================================

class PriceService:
    """Serviço para obter preços de criptomoedas em tempo real"""
    
    @staticmethod
    async def get_eth_price_usd() -> float:
        """Obtém o preço atual do ETH em USD"""
        try:
            # Tentar CoinGecko API primeiro (gratuita e confiável)
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("ethereum", {}).get("usd", 3000))
            
            # Fallback para CryptoCompare
            response = requests.get(
                "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("USD", 3000))
                
        except Exception as e:
            print(f"⚠️ Erro ao obter preço do ETH: {e}")
        
        # Fallback para preço aproximado
        return 3000.0

# ========================================
# DOMAIN LAYER - Entidades e Enums
# ========================================

class TestMode(Enum):
    """Modos de teste disponíveis"""
    SIMULATION = "simulation"
    REAL_BLOCKCHAIN = "real"
    RULES_VALIDATION = "rules"
    INTEGRATED = "integrated"

class TestSeverity(Enum):
    """Níveis de severidade dos testes"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class TestResult:
    """Resultado de um teste específico"""
    test_name: str
    success: bool
    data: Dict[str, Any]
    messages: List[str]
    severity: TestSeverity
    execution_time_ms: float

@dataclass
class WalletInfo:
    """Informações detalhadas de uma carteira/contrato"""
    address: str
    is_contract: bool
    age_hours: float
    age_days: float
    first_transaction_date: Optional[str]
    transaction_count: int

@dataclass
class TransactionAnalysis:
    """Resultado da análise de uma transação"""
    transaction_hash: str
    value_eth: float
    estimated_usd: float
    is_suspicious: bool
    risk_score: float
    risk_level: str
    triggered_rules: List[str]
    alerts_count: int
    from_wallet: WalletInfo
    to_wallet: WalletInfo
    gas_price_ratio: float
    timestamp: str
    context: Dict[str, Any]

# ========================================
# APPLICATION LAYER - Casos de Uso
# ========================================

class WalletAnalyzer:
    """Classe helper para análise detalhada de carteiras e contratos"""
    
    def __init__(self, etherscan_api_key: Optional[str] = None):
        self.etherscan_api_key = etherscan_api_key or os.getenv("ETHERSCAN_API_KEY")
        
    async def analyze_wallet(self, address: str, web3_provider=None) -> WalletInfo:
        """Analisa uma carteira/contrato e retorna informações detalhadas"""
        try:
            # Verificar se é contrato
            is_contract = await self._is_contract(address, web3_provider)
            
            # Obter idade real da carteira
            age_hours, first_tx_date, tx_count = await self._get_real_wallet_age(address)
            age_days = age_hours / 24 if age_hours else 0
            
            return WalletInfo(
                address=address,
                is_contract=is_contract,
                age_hours=age_hours,
                age_days=age_days,
                first_transaction_date=first_tx_date,
                transaction_count=tx_count
            )
        except Exception as e:
            # Fallback para dados básicos
            return WalletInfo(
                address=address,
                is_contract=False,
                age_hours=168.0,  # 7 dias padrão
                age_days=7.0,
                first_transaction_date=None,
                transaction_count=0
            )
    
    async def _is_contract(self, address: str, web3_provider=None) -> bool:
        """Verifica se um endereço é um contrato"""
        try:
            # Primeiro tentar com Web3/Infura se disponível
            if web3_provider and hasattr(web3_provider, 'w3'):
                code = web3_provider.w3.eth.get_code(address)
                return len(code) > 0
            
            # Fallback para Etherscan API
            if self.etherscan_api_key:
                import requests
                url = f"https://api.etherscan.io/api"
                params = {
                    "module": "proxy",
                    "action": "eth_getCode",
                    "address": address,
                    "tag": "latest",
                    "apikey": self.etherscan_api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    code = data.get("result", "0x")
                    return code != "0x" and len(code) > 2
        except Exception:
            pass
        
        return False
    
    async def _get_real_wallet_age(self, address: str) -> tuple[float, Optional[str], int]:
        """Obtém a idade real da carteira via Etherscan API com melhor tratamento de erros"""
        if not self.etherscan_api_key:
            return 168.0, None, 0  # 7 dias padrão
        
        try:
            import requests
            from datetime import datetime
            import time
            
            # Adicionar delay para evitar rate limiting
            await asyncio.sleep(0.2)
            
            # Obter primeira transação
            url = "https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 1,  # Apenas primeira transação
                "sort": "asc",
                "apikey": self.etherscan_api_key
            }
            
            response = requests.get(url, params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "1" and data.get("result"):
                    transactions = data["result"]
                    if transactions and len(transactions) > 0:
                        first_tx = transactions[0]
                        timestamp = int(first_tx["timeStamp"])
                        first_date = datetime.fromtimestamp(timestamp)
                        
                        # Calcular idade em horas
                        now = datetime.now()
                        age_hours = (now - first_date).total_seconds() / 3600
                        
                        # Obter total de transações
                        total_tx_count = await self._get_transaction_count(address)
                        
                        return age_hours, first_date.isoformat(), total_tx_count
                elif data.get("status") == "0":
                    # Carteira sem transações ou erro
                    return 0.0, None, 0
            
            return 168.0, None, 0  # Fallback
            
        except Exception as e:
            print(f"⚠️ Erro ao obter idade da carteira {address[:10]}...: {e}")
            return 168.0, None, 0  # Fallback
    
    async def _get_transaction_count(self, address: str) -> int:
        """Obtém o número total de transações de uma carteira"""
        if not self.etherscan_api_key:
            return 0
        
        try:
            import requests
            
            url = "https://api.etherscan.io/api"
            params = {
                "module": "proxy",
                "action": "eth_getTransactionCount",
                "address": address,
                "tag": "latest",
                "apikey": self.etherscan_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", "0x0")
                return int(result, 16)  # Converter de hex para decimal
                
        except Exception:
            pass
        
        return 0

class TestCase(ABC):
    """Interface para casos de teste"""
    
    @abstractmethod
    async def execute(self) -> TestResult:
        """Executa o teste e retorna o resultado"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome do teste"""
        pass

class SystemHealthTest(TestCase):
    """Testa conectividade e saúde do sistema"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
    
    def get_name(self) -> str:
        return "System Health Check"
    
    async def execute(self) -> TestResult:
        start_time = datetime.now()
        messages = []
        success = True
        data = {}
        
        try:
            # Teste de conectividade da API
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                data["api_status"] = "healthy"
                data["components"] = health_data.get("components", {})
                messages.append("✅ API conectada e operacional")
            else:
                success = False
                messages.append(f"❌ API retornou status {response.status_code}")
                
            # Verificar configurações de ambiente
            config_checks = {
                "INFURA_URL": os.getenv("INFURA_URL"),
                "ETHERSCAN_API_KEY": os.getenv("ETHERSCAN_API_KEY"),
                "DATABASE_URL": os.getenv("DATABASE_URL")
            }
            
            data["environment"] = {}
            for key, value in config_checks.items():
                configured = bool(value)
                data["environment"][key] = configured
                status = "✅" if configured else "⚠️"
                messages.append(f"{status} {key}: {'Configurado' if configured else 'Não configurado'}")
            
        except Exception as e:
            success = False
            messages.append(f"❌ Erro na verificação: {e}")
            data["error"] = str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        severity = TestSeverity.INFO if success else TestSeverity.ERROR
        
        return TestResult(
            test_name=self.get_name(),
            success=success,
            data=data,
            messages=messages,
            severity=severity,
            execution_time_ms=execution_time
        )

class RulesValidationTest(TestCase):
    """Testa configuração e funcionamento das regras"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
    
    def get_name(self) -> str:
        return "Rules Validation Test"
    
    async def execute(self) -> TestResult:
        start_time = datetime.now()
        messages = []
        success = True
        data = {}
        
        try:
            # Recarregar regras
            reload_response = requests.post(f"{self.api_url}/api/v1/rules/reload")
            if reload_response.status_code == 200:
                messages.append("✅ Regras recarregadas com sucesso")
            else:
                messages.append("⚠️ Falha ao recarregar regras")
            
            # Verificar regras ativas
            rules_response = requests.get(f"{self.api_url}/api/v1/rules")
            if rules_response.status_code == 200:
                rules_data = rules_response.json()
                data["total_active"] = rules_data.get("total_active", 0)
                data["total_configured"] = rules_data.get("total_configured", 0)
                data["active_rules"] = [rule["name"] for rule in rules_data.get("active_rules", [])]
                
                messages.append(f"📊 Regras ativas: {data['total_active']}")
                messages.append(f"📝 Regras configuradas: {data['total_configured']}")
                
                for rule_name in data["active_rules"]:
                    messages.append(f"   • {rule_name.replace('_', ' ').title()}")
            
            # Teste com transação suspeita
            test_transaction = {
                "hash": "0xtest_high_value_suspicious",
                "from_address": "0x742d35cc6671c3f5c32cf8e0f4f85b1e4f8c8c1a",
                "to_address": "0x8ba1f109551bd432803012645hac136c0d8f8e56",
                "value": 15000.0,  # Alto valor
                "gas_price": 80.0,  # Gas alto
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "block_number": 18500000,
                "transaction_type": "TRANSFER"
            }
            
            analysis_response = requests.post(
                f"{self.api_url}/api/v1/analyze/transaction",
                json=test_transaction,
                headers={"Content-Type": "application/json"}
            )
            
            if analysis_response.status_code == 200:
                result = analysis_response.json()
                analysis = result["analysis_result"]
                
                data["test_analysis"] = {
                    "is_suspicious": analysis.get("is_suspicious", False),
                    "risk_score": analysis.get("risk_score", 0),
                    "triggered_rules": analysis.get("triggered_rules", []),
                    "alert_count": analysis.get("alert_count", 0)
                }
                
                messages.append("🧪 Teste de regras executado com sucesso")
                if data["test_analysis"]["triggered_rules"]:
                    messages.append(f"🎯 Regras ativadas: {len(data['test_analysis']['triggered_rules'])}")
                else:
                    success = False
                    messages.append("⚠️ Nenhuma regra foi ativada para transação suspeita")
            
        except Exception as e:
            success = False
            messages.append(f"❌ Erro na validação de regras: {e}")
            data["error"] = str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        severity = TestSeverity.INFO if success else TestSeverity.WARNING
        
        return TestResult(
            test_name=self.get_name(),
            success=success,
            data=data,
            messages=messages,
            severity=severity,
            execution_time_ms=execution_time
        )

class BlockchainDataTest(TestCase):
    """Testa captura de dados da blockchain"""
    
    def __init__(self, mode: TestMode = TestMode.SIMULATION, api_url: str = "http://localhost:5000"):
        self.mode = mode
        self.api_url = api_url
    
    def get_name(self) -> str:
        return f"Blockchain Data Test ({self.mode.value})"
    
    async def execute(self) -> TestResult:
        start_time = datetime.now()
        messages = []
        success = True
        data = {}
        
        try:
            # Configurar modo
            blockchain_mode = "real" if self.mode == TestMode.REAL_BLOCKCHAIN else "simulation"
            
            if blockchain_mode == "real" and not os.getenv("INFURA_URL"):
                blockchain_mode = "simulation"
                messages.append("⚠️ INFURA_URL não configurado, usando simulação")
            
            data["execution_mode"] = blockchain_mode
            
            # Criar provedor blockchain
            monitor = ContinuousMonitor(api_url=self.api_url, mode=blockchain_mode)
            
            # Obter transação para análise
            if blockchain_mode == "real":
                transaction = await self._get_real_transaction(monitor)
                messages.append("🌐 Usando dados reais da blockchain Ethereum")
            else:
                transaction = await self._get_simulated_transaction(monitor)
                messages.append("🎭 Usando dados simulados")
            
            if not transaction:
                raise Exception("Falha ao obter transação para teste")
            
            # Registrar dados da transação com hashes completas
            data["transaction"] = {
                "hash": transaction["hash"],
                "value_eth": transaction["value"],
                "estimated_usd": transaction["value"] * 3000,
                "gas_price": transaction["gas_price"],
                "from_address": transaction["from_address"],
                "to_address": transaction.get("to_address", "N/A"),
                "block_number": transaction.get("block_number", "N/A"),
                "timestamp": transaction.get("timestamp", datetime.now().isoformat())
            }
            
            # Analisar transação
            analysis = await self._analyze_transaction(monitor, transaction)
            if analysis:
                data["analysis"] = analysis
                messages.append("✅ Análise de fraude executada com sucesso")
                messages.append(f"🎯 Risk Score: {analysis.risk_score:.3f}")
                messages.append(f"📊 Regras ativadas: {len(analysis.triggered_rules)}")
                
                # Detalhes das carteiras
                self._add_wallet_messages(messages, analysis.from_wallet, "📤 Carteira Origem")
                if analysis.to_wallet.address != "N/A":
                    self._add_wallet_messages(messages, analysis.to_wallet, "� Carteira Destino")
            else:
                success = False
                messages.append("❌ Falha na análise da transação")
            
        except Exception as e:
            success = False
            messages.append(f"❌ Erro no teste de blockchain: {e}")
            data["error"] = str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        severity = TestSeverity.INFO if success else TestSeverity.ERROR
        
        return TestResult(
            test_name=self.get_name(),
            success=success,
            data=data,
            messages=messages,
            severity=severity,
            execution_time_ms=execution_time
        )
    
    def _add_wallet_messages(self, messages: List[str], wallet: WalletInfo, prefix: str):
        """Adiciona mensagens detalhadas sobre uma carteira"""
        if wallet.address == "N/A":
            return
            
        wallet_type = "📜 Contrato" if wallet.is_contract else "👤 EOA (Externally Owned Account)"
        messages.append(f"   {prefix}: {wallet_type}")
        messages.append(f"      • Endereço: {wallet.address}")
        
        if wallet.age_hours > 0:
            if wallet.age_days >= 365:
                age_str = f"{wallet.age_days/365:.1f} anos"
            elif wallet.age_days >= 1:
                age_str = f"{wallet.age_days:.1f} dias"
            else:
                age_str = f"{wallet.age_hours:.1f} horas"
            
            messages.append(f"      • 📅 Idade: {age_str}")
            
            if wallet.first_transaction_date:
                messages.append(f"      • 🗓️ Primeira TX: {wallet.first_transaction_date[:10]}")
        
        if wallet.transaction_count > 0:
            messages.append(f"      • 📊 Total de TXs: {wallet.transaction_count}")
    
    async def _get_real_transaction(self, monitor: ContinuousMonitor) -> Optional[Dict]:
        """Obtém transação real da blockchain"""
        try:
            latest_block = await monitor.blockchain_provider.get_latest_block()
            if not latest_block:
                return None
            
            # Buscar transações com valor em vários blocos
            for i in range(5):  # Verificar últimos 5 blocos
                block_num = latest_block - i
                transactions = await monitor.blockchain_provider.get_block_transactions(block_num)
                
                # Filtrar transações com valor > 0
                value_transactions = [tx for tx in transactions if tx.get("value", 0) > 0]
                if value_transactions:
                    # Retornar transação com maior valor
                    return max(value_transactions, key=lambda x: x["value"])
            
            # Fallback para qualquer transação
            transactions = await monitor.blockchain_provider.get_block_transactions(latest_block)
            return transactions[0] if transactions else None
            
        except Exception:
            return None
    
    async def _get_simulated_transaction(self, monitor: ContinuousMonitor) -> Optional[Dict]:
        """Obtém transação simulada"""
        try:
            transactions = await monitor.blockchain_provider._get_simulated_transactions()
            return transactions[0] if transactions else None
        except Exception:
            return None
    
    async def _analyze_transaction(self, monitor: ContinuousMonitor, transaction: Dict) -> Optional[TransactionAnalysis]:
        """Analisa transação e retorna resultado estruturado com informações detalhadas das carteiras"""
        try:
            # Criar analyzer para carteiras
            wallet_analyzer = WalletAnalyzer()
            
            # Analisar carteiras origem e destino
            from_wallet = await wallet_analyzer.analyze_wallet(
                transaction["from_address"], 
                monitor.blockchain_provider if hasattr(monitor.blockchain_provider, 'w3') else None
            )
            
            to_wallet = await wallet_analyzer.analyze_wallet(
                transaction.get("to_address", ""), 
                monitor.blockchain_provider if hasattr(monitor.blockchain_provider, 'w3') else None
            ) if transaction.get("to_address") else WalletInfo("N/A", False, 0, 0, None, 0)
            
            # Executar análise de fraude
            result = await monitor.analyze_transaction(transaction)
            if not result:
                return None
            
            analysis_data = result.get("analysis_result", {})
            context = result.get("context", {})
            
            # Obter preço real do ETH
            eth_price_usd = await PriceService.get_eth_price_usd()
            
            # Processar timestamp da transação
            timestamp = transaction.get("timestamp", transaction.get("block_timestamp", ""))
            formatted_timestamp = "N/A"
            
            if timestamp:
                try:
                    # Se timestamp for string ISO
                    if isinstance(timestamp, str):
                        if timestamp.endswith('Z'):
                            timestamp = timestamp[:-1] + '+00:00'
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    # Se timestamp for epoch (int/float)
                    elif isinstance(timestamp, (int, float)):
                        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        formatted_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                except Exception as e:
                    print(f"⚠️ Erro ao processar timestamp: {e}")
                    formatted_timestamp = str(timestamp)
            
            return TransactionAnalysis(
                transaction_hash=transaction["hash"],
                value_eth=transaction["value"],
                estimated_usd=transaction["value"] * eth_price_usd,
                is_suspicious=analysis_data.get("is_suspicious", False),
                risk_score=analysis_data.get("risk_score", 0.0),
                risk_level=analysis_data.get("risk_level", "LOW"),
                triggered_rules=analysis_data.get("triggered_rules", []),
                alerts_count=analysis_data.get("alert_count", 0),
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                gas_price_ratio=context.get("gas_price_ratio", 1.0),
                timestamp=formatted_timestamp,
                context=context
            )
        except Exception as e:
            print(f"⚠️ Erro na análise de transação: {e}")
            return None

# ========================================
# INFRASTRUCTURE LAYER - Apresentação
# ========================================

class TestReporter:
    """Responsável por formatar e exibir resultados dos testes"""
    
    @staticmethod
    def print_header():
        """Exibe cabeçalho do sistema de testes"""
        print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║        🛡️  TecBan Integrated Testing Suite                ║
    ║                                                          ║
    ║    Sistema Integrado de Testes de Detecção de Fraudes    ║
    ║                     v2.0.0                               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
        """)
    
    @staticmethod
    def print_test_result(result: TestResult):
        """Exibe resultado de um teste específico"""
        status_icon = "✅" if result.success else "❌"
        severity_icons = {
            TestSeverity.INFO: "🔵",
            TestSeverity.WARNING: "🟡", 
            TestSeverity.ERROR: "🔴",
            TestSeverity.CRITICAL: "🟣"
        }
        
        print(f"\n{'-'*80}")
        print(f"{status_icon} {severity_icons[result.severity]} {result.test_name}")
        print(f"⏱️  Tempo de execução: {result.execution_time_ms:.1f}ms")
        print(f"{'-'*80}")
        
        for message in result.messages:
            print(f"   {message}")
        
        if result.data and result.success:
            TestReporter._print_test_data(result.data)
    
    @staticmethod
    def _print_test_data(data: Dict[str, Any]):
        """Exibe dados estruturados do teste no formato organizado solicitado"""
        if "transaction" in data and "analysis" in data:
            tx = data["transaction"]
            analysis = data["analysis"]
            
            if isinstance(analysis, TransactionAnalysis):
                print(f"\n   📊 ANÁLISE DE TRANSAÇÃO")
                print(f"   {'='*50}")
                
                # Data da transação - usar timestamp processado
                formatted_timestamp = analysis.timestamp
                # Extrair apenas a data se for timestamp completo
                if formatted_timestamp and formatted_timestamp != "N/A":
                    if "UTC" in formatted_timestamp:
                        # Formato: "2025-08-22 14:30:45 UTC"
                        date_part = formatted_timestamp.split(" ")[0]
                    elif "T" in formatted_timestamp:
                        # Formato ISO: "2025-08-22T14:30:45Z"
                        date_part = formatted_timestamp.split("T")[0]
                    else:
                        date_part = formatted_timestamp
                else:
                    date_part = "N/A"
                
                print(f"   Data da Transação: {date_part}")
                print(f"   Hora da Transação: {formatted_timestamp}")
                
                # Hash da transação
                print(f"   Hash da Transação: {tx.get('hash', 'N/A')}")
                
                # Carteira de origem
                print(f"   Carteira de Origem: {'📜 Contrato' if analysis.from_wallet.is_contract else '👤 EOA'}")
                print(f"     Endereço: {analysis.from_wallet.address}")
                
                # Idade da carteira origem
                if analysis.from_wallet.age_hours > 0:
                    if analysis.from_wallet.age_days >= 365:
                        age_str = f"{analysis.from_wallet.age_days/365:.1f} anos"
                    elif analysis.from_wallet.age_days >= 1:
                        age_str = f"{analysis.from_wallet.age_days:.1f} dias"
                    else:
                        age_str = f"{analysis.from_wallet.age_hours:.1f} horas"
                    print(f"     Idade: {age_str}")
                else:
                    print(f"     Idade: Não disponível")
                
                # Carteira de destino
                if analysis.to_wallet.address != "N/A":
                    print(f"   Carteira de Destino: {'📜 Contrato' if analysis.to_wallet.is_contract else '👤 EOA'}")
                    print(f"     Endereço: {analysis.to_wallet.address}")
                    
                    # Idade da carteira destino
                    if analysis.to_wallet.age_hours > 0:
                        if analysis.to_wallet.age_days >= 365:
                            age_str = f"{analysis.to_wallet.age_days/365:.1f} anos"
                        elif analysis.to_wallet.age_days >= 1:
                            age_str = f"{analysis.to_wallet.age_days:.1f} dias"
                        else:
                            age_str = f"{analysis.to_wallet.age_hours:.1f} horas"
                        print(f"     Idade: {age_str}")
                    else:
                        print(f"     Idade: Não disponível")
                
                # Valor e Gas Price
                print(f"   Valor: {analysis.value_eth:.6f} ETH (≈ ${analysis.estimated_usd:.2f})")
                print(f"   Gas Price: {tx.get('gas_price', 0):.3f} Gwei")
                
                print(f"\n   Resultado da Análise:")
                print(f"     Suspeito: {'🚨 SIM' if analysis.is_suspicious else '✅ NÃO'}")
                print(f"     Risk Score: {analysis.risk_score:.3f}")
                print(f"     Nível: {analysis.risk_level}")
                print(f"     Regras ativadas: {len(analysis.triggered_rules)}")
                
                if analysis.triggered_rules:
                    rules_str = ", ".join(analysis.triggered_rules)
                    print(f"     Regras: {rules_str}")
    
    @staticmethod
    def _print_wallet_info(wallet: WalletInfo):
        """Exibe informações detalhadas de uma carteira"""
        wallet_type = "📜 Contrato" if wallet.is_contract else "👤 EOA"
        print(f"      • Tipo: {wallet_type}")
        print(f"      • Endereço: {wallet.address}")
        
        if wallet.age_hours > 0:
            if wallet.age_days >= 365:
                age_str = f"{wallet.age_days/365:.1f} anos"
            elif wallet.age_days >= 1:
                age_str = f"{wallet.age_days:.1f} dias"
            else:
                age_str = f"{wallet.age_hours:.1f} horas"
            
            print(f"      • 📅 Idade: {age_str}")
            
            if wallet.first_transaction_date:
                print(f"      • 🗓️ Primeira TX: {wallet.first_transaction_date[:10]}")
        
        if wallet.transaction_count > 0:
            print(f"      • 📊 Total de TXs: {wallet.transaction_count}")
    
    @staticmethod
    def print_summary(results: List[TestResult]):
        """Exibe resumo final dos testes"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        total_time = sum(r.execution_time_ms for r in results)
        
        print(f"\n{'='*80}")
        print(f"📊 RESUMO FINAL DOS TESTES")
        print(f"{'='*80}")
        print(f"   • Total de testes: {total_tests}")
        print(f"   • Sucessos: {successful_tests}")
        print(f"   • Falhas: {total_tests - successful_tests}")
        print(f"   • Tempo total: {total_time:.1f}ms")
        print(f"   • Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
        
        # Mostrar falhas
        failed_tests = [r for r in results if not r.success]
        if failed_tests:
            print(f"\n❌ TESTES COM FALHA:")
            for test in failed_tests:
                print(f"   • {test.test_name}: {test.severity.value}")

# ========================================
# APPLICATION LAYER - Orchestrator
# ========================================

class TestSuite:
    """Orquestrador principal dos testes"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.reporter = TestReporter()
    
    async def run_quick_check(self) -> List[TestResult]:
        """Executa verificação rápida do sistema"""
        test_cases = [
            SystemHealthTest(self.api_url),
            RulesValidationTest(self.api_url),
            BlockchainDataTest(TestMode.SIMULATION, self.api_url)
        ]
        
        return await self._execute_tests(test_cases)
    
    async def run_full_test(self) -> List[TestResult]:
        """Executa suite completa de testes"""
        test_cases = [
            SystemHealthTest(self.api_url),
            RulesValidationTest(self.api_url),
            BlockchainDataTest(TestMode.SIMULATION, self.api_url),
            BlockchainDataTest(TestMode.REAL_BLOCKCHAIN, self.api_url)
        ]
        
        return await self._execute_tests(test_cases)
    
    async def run_blockchain_comparison(self) -> List[TestResult]:
        """Compara dados simulados vs reais"""
        test_cases = [
            SystemHealthTest(self.api_url),
            BlockchainDataTest(TestMode.SIMULATION, self.api_url),
            BlockchainDataTest(TestMode.REAL_BLOCKCHAIN, self.api_url)
        ]
        
        return await self._execute_tests(test_cases)
    
    async def _execute_tests(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Executa lista de casos de teste"""
        results = []
        
        for test_case in test_cases:
            try:
                result = await test_case.execute()
                results.append(result)
                self.reporter.print_test_result(result)
            except Exception as e:
                error_result = TestResult(
                    test_name=test_case.get_name(),
                    success=False,
                    data={"error": str(e)},
                    messages=[f"❌ Erro crítico na execução: {e}"],
                    severity=TestSeverity.CRITICAL,
                    execution_time_ms=0
                )
                results.append(error_result)
                self.reporter.print_test_result(error_result)
        
        return results

# ========================================
# INTERFACE LAYER - CLI
# ========================================

class TestCLI:
    """Interface de linha de comando para os testes"""
    
    def __init__(self):
        self.suite = TestSuite()
        self.reporter = TestReporter()
    
    async def run_interactive(self):
        """Executa interface interativa"""
        self.reporter.print_header()
        
        print("🤔 Escolha o tipo de teste:")
        print("1. 🚀 Verificação Rápida (Health + Rules + Simulation)")
        print("2. 🔬 Teste Completo (+ Blockchain Real)")
        print("3. ⚖️  Comparação Simulado vs Real")
        print("4. 🛠️  Apenas Validação de Regras")
        print("5. 🌐 Apenas Dados Blockchain Real")
        
        try:
            choice = input("\nEscolha (1-5): ").strip()
            
            if choice == "1":
                results = await self.suite.run_quick_check()
            elif choice == "2":
                results = await self.suite.run_full_test()
            elif choice == "3":
                results = await self.suite.run_blockchain_comparison()
            elif choice == "4":
                results = [await RulesValidationTest().execute()]
                self.reporter.print_test_result(results[0])
            elif choice == "5":
                results = [await BlockchainDataTest(TestMode.REAL_BLOCKCHAIN).execute()]
                self.reporter.print_test_result(results[0])
            else:
                print("❌ Opção inválida")
                return
            
            self.reporter.print_summary(results)
            
        except KeyboardInterrupt:
            print("\n\n⏹️ Testes interrompidos pelo usuário")
        except Exception as e:
            print(f"\n❌ Erro na execução: {e}")

# ========================================
# MAIN ENTRY POINT
# ========================================

async def main():
    """Função principal"""
    cli = TestCLI()
    await cli.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())
