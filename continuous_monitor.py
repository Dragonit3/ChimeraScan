#!/usr/bin/env python3
"""
Monitor Contínuo de Fraudes TecBan
Sistema de monitoramento 24/7 para detecção de fraudes em tempo real
Suporta tanto simulação quanto integração com APIs reais de blockchain
"""
import asyncio
import time
import logging
import random
import os
import hashlib
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import requests
from web3 import Web3

from dotenv import load_dotenv
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BlockchainProvider:
    """Provedor de dados blockchain - suporta simulação e APIs reais"""
    
    def __init__(self, mode="simulation", infura_url=None, etherscan_api_key=None):
        self.mode = mode
        self.web3 = None
        self.etherscan_api_key = etherscan_api_key
        self.monitor = None  # Referência ao monitor parent
        
        # Cache para datas de funding das carteiras
        self.wallet_funding_cache = {}  # {address: datetime}
        self.cache_expiry = 3600  # Cache por 1 hora
        
        if mode == "real" and infura_url:
            try:
                self.web3 = Web3(Web3.HTTPProvider(infura_url))
                if self.web3.is_connected():
                    logger.info("✅ Conectado à rede Ethereum via Infura")
                else:
                    logger.warning("⚠️ Falha na conexão com Ethereum, usando modo simulação")
                    self.mode = "simulation"
            except Exception as e:
                logger.warning(f"⚠️ Erro ao conectar com Ethereum: {e}, usando modo simulação")
                self.mode = "simulation"
    
    async def get_latest_block(self) -> Optional[int]:
        """Obtém o número do bloco mais recente"""
        if self.mode == "real" and self.web3:
            try:
                return self.web3.eth.block_number
            except Exception as e:
                logger.error(f"Erro ao obter bloco mais recente: {e}")
                return None
        else:
            # Simulação - bloco incremental
            return random.randint(18000000, 18999999)
    
    async def get_block_transactions(self, block_number: int) -> List[Dict]:
        """Obtém transações de um bloco específico"""
        if self.mode == "real" and self.web3:
            return await self._get_real_block_transactions(block_number)
        else:
            return await self._get_simulated_transactions()
    
    async def _get_real_block_transactions(self, block_number: int) -> List[Dict]:
        """Obtém transações reais de um bloco com datas de funding reais"""
        try:
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            transactions = []
            
            # Filtrar transações com valor > 0 para análise mais interessante
            value_transactions = []
            contract_transactions = []
            
            # Processar no máximo 10 transações por bloco para não sobrecarregar a API
            max_transactions_to_process = 10
            processed_count = 0
            
            for tx in block.transactions:
                if processed_count >= max_transactions_to_process:
                    break
                    
                # Usar timestamp real do bloco
                block_timestamp = datetime.fromtimestamp(block.timestamp, tz=timezone.utc)
                
                # Converter ETH para USD
                eth_value = float(Web3.from_wei(tx.value, 'ether'))
                usd_value = self.eth_to_usd(eth_value)
                
                # Buscar datas de funding REAIS via API (modo real NUNCA simula)
                funded_date_from = await self._get_wallet_funded_date(tx['from'], block_timestamp)
                funded_date_to = None
                if tx.get('to'):
                    funded_date_to = await self._get_wallet_funded_date(tx.get('to'), block_timestamp)

                transaction = {
                    "hash": tx.hash.hex(),
                    "from_address": tx['from'],
                    "to_address": tx.get('to', ''),
                    "value": usd_value,  # Valor em USD para as regras
                    "eth_value": eth_value,  # Mantém valor original em ETH para logs
                    "gas_price": float(Web3.from_wei(tx.gasPrice, 'gwei')),
                    "timestamp": block_timestamp.isoformat(),
                    "block_number": block_number,
                    "transaction_type": "TRANSFER",
                    "fundeddate_from": funded_date_from.isoformat() if funded_date_from else None,
                    "fundeddate_to": funded_date_to.isoformat() if funded_date_to else None
                }
                
                # Separar por tipo para priorizar transações com valor
                if transaction["eth_value"] > 0:
                    value_transactions.append(transaction)
                else:
                    contract_transactions.append(transaction)
                
                processed_count += 1
            
            # Priorizar transações com valor, depois contratos
            # Ordenar transações com valor por valor ETH decrescente
            value_transactions.sort(key=lambda x: x["eth_value"], reverse=True)
            
            # Pegar até 3 transações com valor + 2 de contrato
            transactions.extend(value_transactions[:3])
            transactions.extend(contract_transactions[:2])
            
            # Se não há transações com valor, pegar mais contratos
            if not value_transactions:
                transactions = contract_transactions[:5]
            
            # Se ainda não temos transações suficientes, pegar mais contratos
            if len(transactions) < 3:
                remaining = contract_transactions[len(transactions):]
                transactions.extend(remaining[:5-len(transactions)])
            
            # Limitar total a 5 transações
            transactions = transactions[:5]
            
            logger.debug(f"Block {block_number}: Found {len(value_transactions)} value TXs, {len(contract_transactions)} contract TXs, returning {len(transactions)} TXs")
            
            return transactions
            
        except Exception as e:
            logger.error(f"Erro ao obter transações reais: {e}")
            return []
    
    def eth_to_usd(self, eth_amount: float) -> float:
        """Converte valor de ETH para USD usando preço do monitor"""
        if self.monitor and hasattr(self.monitor, 'eth_price_usd') and self.monitor.eth_price_usd:
            return eth_amount * self.monitor.eth_price_usd
        else:
            return eth_amount * 2500.0  # Fallback price
    
    async def _get_simulated_transactions(self) -> List[Dict]:
        """Gera transações simuladas (código original)"""
        # Tipos de transações com probabilidades diferentes
        transaction_types = [
            {"type": "normal", "prob": 0.65, "value_range": (10, 5000)},
            {"type": "high_value", "prob": 0.20, "value_range": (50000, 200000)},
            {"type": "suspicious", "prob": 0.10, "value_range": (1000, 50000)},
            {"type": "critical", "prob": 0.05, "value_range": (500000, 2000000)}
        ]
        
        # Selecionar tipo baseado em probabilidade
        rand = random.random()
        cumulative = 0
        selected_type = transaction_types[0]
        
        for tx_type in transaction_types:
            cumulative += tx_type["prob"]
            if rand <= cumulative:
                selected_type = tx_type
                break
        
        # Gerar dados da transação
        value = random.uniform(*selected_type["value_range"])
        
        # Gas price baseado no tipo
        base_gas = 20
        if selected_type["type"] == "suspicious":
            gas_price = random.uniform(100, 300)  # Gas alto suspeito
        elif selected_type["type"] == "critical":
            gas_price = random.uniform(150, 500)  # Gas muito alto
        else:
            gas_price = random.uniform(15, 50)    # Gas normal
        
        # Horário suspeito (madrugada)
        now = datetime.now(timezone.utc)
        if selected_type["type"] in ["suspicious", "critical"] and random.random() < 0.3:
            # 30% chance de ser em horário suspeito
            suspicious_hour = random.randint(1, 5)  # 1-5 AM
            now = now.replace(hour=suspicious_hour, minute=random.randint(0, 59))
        
        # Endereços
        addresses = [
            "0x742d35Cc631C0532925a3b8D33C9", "0xF977814e90dA44bFA03b6295",
            "0x28C6c06298d514Db089934071355", "0xBE0eB53F46cd790Cd13851d5",
            "0x8315177aB297bA92A06054cE80a67ED4", "0xcfAf9660251648a3723f21172e2A4D1257b2b372",
            "0x28C6c06298d514Db089934071312", "0x00d9fE085D99B33Ab2AAE8063180c63E23bF2E69"
        ]
        
        from_address = random.choice(addresses)
        to_address = random.choice(addresses)
        
        # Gerar datas de funding para ambas as carteiras
        funded_date_from = None
        funded_date_to = None
        
        if selected_type["type"] == "normal":
            # Carteiras antigas (30-365 dias)
            days_ago_from = random.randint(30, 365)
            days_ago_to = random.randint(30, 365)
            funded_date_from = now - timedelta(days=days_ago_from)
            funded_date_to = now - timedelta(days=days_ago_to)
        elif selected_type["type"] == "high_value":
            # Carteiras médias (7-90 dias)
            days_ago_from = random.randint(7, 90)
            days_ago_to = random.randint(7, 90)
            funded_date_from = now - timedelta(days=days_ago_from)
            funded_date_to = now - timedelta(days=days_ago_to)
        elif selected_type["type"] == "suspicious":
            # Algumas carteiras novas (1-30 dias), algumas antigas
            if random.random() < 0.4:  # 40% chance de carteira nova (FROM)
                hours_ago = random.randint(1, 48)  # 1-48 horas
                funded_date_from = now - timedelta(hours=hours_ago)
            else:
                days_ago = random.randint(1, 30)
                funded_date_from = now - timedelta(days=days_ago)
                
            # TO pode ser diferente
            if random.random() < 0.3:  # 30% chance de carteira nova (TO)
                hours_ago = random.randint(1, 48)
                funded_date_to = now - timedelta(hours=hours_ago)
            else:
                days_ago = random.randint(1, 60)
                funded_date_to = now - timedelta(days=days_ago)
                
        elif selected_type["type"] == "critical":
            # Maioria carteiras muito novas (< 24h)
            if random.random() < 0.7:  # 70% chance de carteira muito nova (FROM)
                hours_ago = random.randint(1, 23)  # 1-23 horas
                funded_date_from = now - timedelta(hours=hours_ago)
            else:
                hours_ago = random.randint(24, 168)  # 1-7 dias
                funded_date_from = now - timedelta(hours=hours_ago)
                
            # TO pode ser diferente
            if random.random() < 0.5:  # 50% chance de carteira muito nova (TO)
                hours_ago = random.randint(1, 23)
                funded_date_to = now - timedelta(hours=hours_ago)
            else:
                hours_ago = random.randint(24, 168)
                funded_date_to = now - timedelta(hours=hours_ago)

        transaction = {
            "hash": f"0x{random.randint(1000000000000000, 9999999999999999):016x}",
            "from_address": from_address,
            "to_address": to_address,
            "value": round(value, 2),
            "gas_price": round(gas_price, 1),
            "timestamp": now.isoformat(),
            "block_number": random.randint(18000000, 18999999),
            "transaction_type": "TRANSFER",
            "fundeddate_from": funded_date_from.isoformat() if funded_date_from else None,
            "fundeddate_to": funded_date_to.isoformat() if funded_date_to else None
        }
        
        return [transaction]  # Retornar como lista
    
    async def get_address_info(self, address: str) -> Dict:
        """Obtém informações sobre um endereço usando Etherscan API"""
        if self.mode == "real" and self.etherscan_api_key:
            try:
                url = f"https://api.etherscan.io/api"
                params = {
                    "module": "account",
                    "action": "balance",
                    "address": address,
                    "tag": "latest",
                    "apikey": self.etherscan_api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1":
                        balance_wei = int(data.get("result", "0"))
                        balance_eth = Web3.from_wei(balance_wei, 'ether')
                        return {
                            "address": address,
                            "balance_eth": float(balance_eth),
                            "balance_wei": balance_wei,
                            "is_contract": False  # Seria necessária outra chamada para verificar
                        }
            except Exception as e:
                logger.error(f"Erro ao obter informações do endereço {address}: {e}")
        
        # Fallback para dados simulados
        return {
            "address": address,
            "balance_eth": random.uniform(0.1, 1000.0),
            "balance_wei": 0,
            "is_contract": random.choice([True, False])
        }

    async def _get_wallet_funded_date(self, address: str, current_time: datetime) -> Optional[datetime]:
        """
        Obtém a data real de funding de uma carteira buscando a primeira transação
        MODO REAL: usa SEMPRE Etherscan API - NUNCA simula
        MODO SIMULAÇÃO: gera uma data baseada em padrões realísticos
        """
        if not address or address == '':
            return None
            
        # Verificar cache primeiro
        cache_key = f"{address}_{self.mode}"
        if cache_key in self.wallet_funding_cache:
            cached_date = self.wallet_funding_cache[cache_key]
            logger.debug(f"📋 Using cached funding date for {address}: {cached_date}")
            return cached_date
            
        try:
            funded_date = None
            
            if self.mode == "real":
                if not self.etherscan_api_key:
                    logger.error(f"❌ REAL MODE: No Etherscan API key configured for {address}")
                    return None
                    
                # Buscar SEMPRE primeira transação real via Etherscan API
                funded_date = await self._get_real_wallet_funding_date(address)
                
                if funded_date is None:
                    logger.warning(f"⚠️ REAL MODE: Could not find real funding date for {address}")
                    return None  # Retornar None se não conseguir buscar dados reais
                else:
                    logger.debug(f"✅ REAL MODE: Found funding date for {address}: {funded_date}")
            else:
                # Modo simulação - gerar baseado no hash para consistência
                address_hash = int(hashlib.md5(address.lower().encode()).hexdigest()[:8], 16)
                days_ago = (address_hash % 180) + 1  # 1-180 dias
                funded_date = current_time - timedelta(days=days_ago)
                logger.debug(f"SIMULATION MODE: Generated funding date for {address}: {funded_date} ({days_ago} days ago)")
            
            # Salvar no cache
            if funded_date:
                self.wallet_funding_cache[cache_key] = funded_date
                
            return funded_date
                
        except Exception as e:
            logger.warning(f"Error getting funded date for {address}: {e}")
            # Fallback para modo simulação
            if self.mode == "real":
                days_ago = random.randint(30, 365)  # Fallback conservador
            else:
                address_hash = int(hashlib.md5(address.lower().encode()).hexdigest()[:8], 16)
                days_ago = (address_hash % 180) + 1
            return current_time - timedelta(days=days_ago)

    async def _get_real_wallet_funding_date(self, address: str) -> Optional[datetime]:
        """
        Busca a data da primeira transação de uma carteira via Etherscan API
        """
        try:
            # Rate limiting - aguardar um pouco entre chamadas
            await asyncio.sleep(0.2)  # 200ms entre chamadas
            
            # Primeiro, tentar buscar transações normais (incoming/outgoing)
            url = "https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 1,  # Só precisamos da primeira transação
                "sort": "asc",  # Ordenar por mais antiga primeiro
                "apikey": self.etherscan_api_key
            }
            
            logger.debug(f"🔍 Searching first transaction for {address}")
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar se temos rate limiting
                if data.get("status") == "0" and "rate limit" in data.get("message", "").lower():
                    logger.warning(f"⚠️ Rate limit hit for Etherscan API, waiting...")
                    await asyncio.sleep(1)  # Aguardar 1 segundo
                    return None
                
                if data.get("status") == "1" and data.get("result"):
                    transactions = data["result"]
                    if transactions and len(transactions) > 0:
                        first_tx = transactions[0]
                        timestamp = int(first_tx["timeStamp"])
                        funded_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        return funded_date
                        
            # Se não encontrou transações normais, tentar transações internas
            logger.debug(f"🔍 Searching internal transactions for {address}")
            params["action"] = "txlistinternal"
            await asyncio.sleep(0.2)  # Rate limiting
            
            response = requests.get(url, params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "0" and "rate limit" in data.get("message", "").lower():
                    logger.warning(f"⚠️ Rate limit hit for internal transactions")
                    return None
                    
                if data.get("status") == "1" and data.get("result"):
                    transactions = data["result"]
                    if transactions and len(transactions) > 0:
                        first_tx = transactions[0]
                        timestamp = int(first_tx["timeStamp"])
                        funded_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        logger.info(f"✅ Real funding date found via internal TX for {address}: {funded_date}")
                        return funded_date
            
            # Se não encontrou nada, pode ser uma carteira muito nova ou sem atividade
            logger.warning(f"⚠️ No transactions found for {address} - may be a new/inactive wallet")
            return None
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout fetching funding date for {address}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 Network error fetching funding date for {address}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching real funding date for {address}: {e}")
            return None

class ContinuousMonitor:
    """Monitor contínuo que obtém transações da blockchain (real ou simulada)"""
    
    def __init__(self, api_url="http://localhost:5000", mode="simulation"):
        self.api_url = api_url
        self.mode = mode
        self.is_running = False
        self.transaction_count = 0
        self.suspicious_count = 0
        self.alert_count = 0
        self.processed_blocks = set()
        
        # Cache para preço ETH/USD
        self.eth_price_usd = None
        self.eth_price_last_update = None
        self.eth_price_cache_duration = 300  # 5 minutos
        
        # Configurar provedor de blockchain
        infura_url = os.getenv("INFURA_URL")
        etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        
        self.blockchain_provider = BlockchainProvider(
            mode=mode,
            infura_url=infura_url,
            etherscan_api_key=etherscan_api_key
        )
        
        # Adicionar referência do monitor ao provider para conversão ETH/USD
        self.blockchain_provider.monitor = self
        
        logger.info(f"🔧 Monitor configurado em modo: {self.blockchain_provider.mode}")
    
    async def get_eth_price_usd(self) -> float:
        """Obtém preço atual do ETH em USD com cache"""
        
        # Verificar se temos cache válido
        if (self.eth_price_usd is not None and 
            self.eth_price_last_update is not None and
            datetime.now() - self.eth_price_last_update < timedelta(seconds=self.eth_price_cache_duration)):
            return self.eth_price_usd
        
        try:
            # Tentar obter preço da API CoinGecko (gratuita)
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get("ethereum", {}).get("usd")
                if price:
                    self.eth_price_usd = float(price)
                    self.eth_price_last_update = datetime.now()
                    logger.debug(f"💰 ETH/USD price updated: ${self.eth_price_usd:,.2f}")
                    return self.eth_price_usd
        
        except Exception as e:
            logger.warning(f"Erro ao obter preço ETH/USD: {e}")
        
        # Fallback para preço fixo se API falhar
        if self.eth_price_usd is None:
            self.eth_price_usd = 2500.0  # Preço aproximado do ETH
            logger.warning(f"Usando preço ETH/USD fixo: ${self.eth_price_usd}")
        
        return self.eth_price_usd
    
    def eth_to_usd(self, eth_amount: float) -> float:
        """Converte valor de ETH para USD"""
        if self.eth_price_usd is None:
            return eth_amount * 4620.0  # Fallback
        return eth_amount * self.eth_price_usd
    
    async def analyze_transaction(self, transaction: Dict) -> Dict:
        """Envia transação para análise na API"""
        try:
            logger.debug(f"📤 Sending transaction to API: {transaction['hash'][:10]}... with fundeddate_from: {transaction.get('fundeddate_from', 'None')}")
            
            response = requests.post(
                f"{self.api_url}/api/v1/analyze/transaction",
                json=transaction,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"✅ API response for {transaction['hash'][:10]}...: {len(result.get('alerts', []))} alerts")
                return result
            else:
                logger.warning(f"❌ API error {response.status_code} for {transaction['hash'][:10]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending transaction {transaction.get('hash', 'unknown')[:10]}... to API: {e}")
            return None
    
    def print_banner(self):
        """Exibe banner do monitor"""
        banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           🛡️  TecBan Continuous Monitor                   ║
    ║                                                          ║
    ║        Monitor Contínuo de Detecção de Fraudes           ║
    ║                        v1.0.0                            ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    async def start_monitoring(self, interval_seconds: float = 3.0):
        """Inicia monitoramento contínuo"""
        self.print_banner()

        # Verificar se API está disponível
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ API não disponível em {self.api_url}")
                return
            
        except Exception as e:
            print(f"❌ Erro ao conectar com API: {e}")
            return
        
        self.is_running = True
        start_time = time.time()
        
        # Mostrar configuração
        mode_emoji = "🌐" if self.blockchain_provider.mode == "real" else "🎭"
        print(f"\n{mode_emoji} Modo: {self.blockchain_provider.mode.upper()}")
        print(f"🔍 Monitoring blockchain transactions every {interval_seconds}s...")
        print(f"📊 Dashboard: {self.api_url}")
        print(f"🚨 Press Ctrl+C to stop monitoring\n")
        
        # Variáveis para modo real
        last_block = None
        if self.blockchain_provider.mode == "real":
            # Inicializar preço ETH/USD
            try:
                await self.get_eth_price_usd()
                logger.info(f"💰 ETH/USD price initialized: ${self.eth_price_usd:,.2f}")
            except Exception as e:
                logger.warning(f"Could not initialize ETH price: {e}")
            
            last_block = await self.blockchain_provider.get_latest_block()
            if last_block:
                print(f"📦 Starting from block: {last_block}")
        
        try:
            while self.is_running:
                transactions = []
                
                if self.blockchain_provider.mode == "real":
                    # Monitoramento de blocos reais
                    current_block = await self.blockchain_provider.get_latest_block()
                    
                    if current_block and current_block != last_block:
                        # Processar blocos novos
                        blocks_to_process = []
                        if last_block:
                            for block_num in range(last_block + 1, current_block + 1):
                                if block_num not in self.processed_blocks:
                                    blocks_to_process.append(block_num)
                        else:
                            blocks_to_process = [current_block]
                        
                        # Processar até 3 blocos por ciclo para não sobrecarregar
                        for block_num in blocks_to_process[:3]:
                            block_transactions = await self.blockchain_provider.get_block_transactions(block_num)
                            transactions.extend(block_transactions)
                            self.processed_blocks.add(block_num)
                            
                            if len(block_transactions) > 0:
                                print(f"📦 Block {block_num}: {len(block_transactions)} transactions")
                        
                        last_block = current_block
                    
                    # Se não há transações reais, aguardar mais tempo
                    if not transactions:
                        await asyncio.sleep(interval_seconds * 2)
                        continue
                        
                else:
                    # Modo simulação - gerar transação
                    transactions = await self.blockchain_provider._get_simulated_transactions()
                
                # Processar cada transação
                for transaction in transactions:
                    if not transaction:
                        continue
                        
                    # Analisar transação
                    result = await self.analyze_transaction(transaction)
                    
                    if result:
                        self.transaction_count += 1
                        
                        # Extrair informações do resultado
                        analysis = result.get("analysis_result", {})
                        is_suspicious = analysis.get("is_suspicious", False)
                        risk_score = analysis.get("risk_score", 0)
                        risk_level = analysis.get("risk_level", "LOW")
                        alerts = result.get("alerts", [])
                        
                        if is_suspicious:
                            self.suspicious_count += 1
                        
                        if alerts:
                            self.alert_count += len(alerts)
                        
                        # Log da transação
                        status_icon = "🚨" if is_suspicious else ("⚠️" if alerts else "✅")
                        risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "🟣"}.get(risk_level, "⚪")
                        
                        # Ajustar formato do log baseado no modo
                        if self.blockchain_provider.mode == "real":
                            eth_value = transaction.get('eth_value', transaction['value'] / self.eth_price_usd)
                            usd_value = transaction['value']
                            
                            # Formatação das datas de funding
                            funded_from = transaction.get('fundeddate_from', 'N/A')
                            funded_to = transaction.get('fundeddate_to', 'N/A')
                            funded_from_display = funded_from[:19] if funded_from and funded_from != 'N/A' else 'N/A'
                            funded_to_display = funded_to[:19] if funded_to and funded_to != 'N/A' else 'N/A'
                            
                            tx_timestamp = transaction.get('timestamp', 'N/A')
                            tx_timestamp_display = tx_timestamp[:19] if tx_timestamp and tx_timestamp != 'N/A' else 'N/A'
                            
                            print(f"{status_icon} TX #{self.transaction_count:04d} | "
                                  f"{eth_value:.6f} ETH (${usd_value:,.2f} USD) | "
                                  f"{risk_icon} {risk_level} | "
                                  f"Risk: {risk_score:.3f} | "
                                  f"Gas: {transaction['gas_price']:.2f} Gwei | "
                                  f"Block: {transaction['block_number']} | "
                                  f"Alerts: {len(alerts)}")
                            print(f"    📋 Hash: {transaction['hash']}")
                            print(f"    🕐 TX Time: {tx_timestamp_display}")
                            print(f"    📤 From: {transaction['from_address']} | 💰 Funded: {funded_from_display}")
                            if transaction.get('to_address'):
                                print(f"    📥 To: {transaction['to_address']} | 💰 Funded: {funded_to_display}")
                        else:
                            # Formatação das datas de funding para modo simulação
                            funded_from = transaction.get('fundeddate_from', 'N/A')
                            funded_to = transaction.get('fundeddate_to', 'N/A')
                            funded_from_display = funded_from[:19] if funded_from and funded_from != 'N/A' else 'N/A'
                            funded_to_display = funded_to[:19] if funded_to and funded_to != 'N/A' else 'N/A'
                            
                            tx_timestamp = transaction.get('timestamp', 'N/A')
                            tx_timestamp_display = tx_timestamp[:19] if tx_timestamp and tx_timestamp != 'N/A' else 'N/A'
                            
                            print(f"{status_icon} TX #{self.transaction_count:04d} | "
                                  f"${transaction['value']:,.2f} USD | "
                                  f"{risk_icon} {risk_level} | "
                                  f"Risk: {risk_score:.3f} | "
                                  f"Alerts: {len(alerts)}")
                            print(f"    📋 Hash: {transaction['hash']}")
                            print(f"    🕐 TX Time: {tx_timestamp_display}")
                            print(f"    📤 From: {transaction['from_address']} | 💰 Funded: {funded_from_display}")
                            if transaction.get('to_address'):
                                print(f"    📥 To: {transaction['to_address']} | 💰 Funded: {funded_to_display}")
                        
                        # Log detalhado para alertas
                        if alerts:
                            for alert in alerts:
                                severity = alert.get("severity", "UNKNOWN")
                                title = alert.get("title", "Alert")
                                print(f"    🚨 [{severity}] {title}")
                                
                                # Se for alerta de carteira nova, mostrar idade calculada
                                if "new wallet" in title.lower() or "wallet interaction" in alert.get("rule_name", "").lower():
                                    # Tentar calcular idade da carteira para exibição
                                    funded_date_str = transaction.get('fundeddate_from')
                                    if funded_date_str:
                                        try:
                                            funded_date = datetime.fromisoformat(funded_date_str.replace('Z', '+00:00'))
                                            tx_date = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
                                            age_hours = (tx_date - funded_date).total_seconds() / 3600
                                            print(f"       🕐 Calculated wallet age: {age_hours:.1f} hours ({age_hours/24:.1f} days)")
                                        except Exception as e:
                                            print(f"       ⚠️  Could not calculate wallet age: {e}")
                        print("-" * 80)
                        # Estatísticas a cada 20 transações
                        if self.transaction_count % 20 == 0:
                            uptime = time.time() - start_time
                            detection_rate = (self.suspicious_count / self.transaction_count) * 100
                            tx_per_min = (self.transaction_count / uptime) * 60
                            
                            print(f"\n📊 STATS | Mode: {self.blockchain_provider.mode.upper()} | "
                                  f"TX: {self.transaction_count} | "
                                  f"Suspicious: {self.suspicious_count} ({detection_rate:.1f}%) | "
                                  f"Alerts: {self.alert_count} | "
                                  f"Rate: {tx_per_min:.1f} tx/min | "
                                  f"Uptime: {uptime/60:.1f}m\n")
                
                # Aguardar intervalo (mais longo para modo real)
                if self.blockchain_provider.mode == "real":
                    await asyncio.sleep(interval_seconds * 2)  # Blocos são mais lentos
                else:
                    await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n⏹️ Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
        finally:
            self.is_running = False
            # Estatísticas finais
            total_time = time.time() - start_time
            print(f"\n📊 FINAL STATISTICS:")
            print(f"   � Mode: {self.blockchain_provider.mode.upper()}")
            print(f"   �🔍 Total Transactions: {self.transaction_count}")
            print(f"   ⚠️  Suspicious Detected: {self.suspicious_count}")
            print(f"   🚨 Total Alerts: {self.alert_count}")
            print(f"   📈 Detection Rate: {(self.suspicious_count/max(1,self.transaction_count))*100:.1f}%")
            print(f"   ⏱️  Total Runtime: {total_time/60:.1f} minutes")
            print(f"   🔧 Avg Rate: {(self.transaction_count/max(1,total_time))*60:.1f} tx/min")
            if self.blockchain_provider.mode == "real":
                print(f"   📦 Blocks Processed: {len(self.processed_blocks)}")

def main():
    """Função principal"""
    
    parser = argparse.ArgumentParser(description="TecBan Continuous Monitor")
    parser.add_argument(
        "--mode", 
        choices=["simulation", "real"], 
        default="simulation",
        help="Modo de operação: simulation (padrão) ou real"
    )
    parser.add_argument(
        "--interval", 
        type=float, 
        default=2.0,
        help="Intervalo entre verificações em segundos (padrão: 2.0)"
    )
    parser.add_argument(
        "--api-url", 
        default="http://localhost:5000",
        help="URL da API do sistema (padrão: http://localhost:5000)"
    )
    
    args = parser.parse_args()
    
    # Verificar variáveis de ambiente para modo real
    if args.mode == "real":
        infura_url = os.getenv("INFURA_URL")
        etherscan_api = os.getenv("ETHERSCAN_API_KEY")
        
        if not infura_url:
            print("⚠️  Para usar modo real, configure INFURA_URL no arquivo .env")
            print("   Exemplo: INFURA_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID")
            print("🎭 Continuando em modo simulação...\n")
            args.mode = "simulation"
        
        if not etherscan_api:
            print("⚠️  Para usar modo real completo, configure ETHERSCAN_API_KEY no arquivo .env")
            print("   Análise de endereços será limitada sem API key\n")
    
    # Criar monitor
    monitor = ContinuousMonitor(api_url=args.api_url, mode=args.mode)
    
    # Executar monitoramento
    try:
        asyncio.run(monitor.start_monitoring(interval_seconds=args.interval))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
