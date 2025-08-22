"""
Monitor de Blockchain Ethereum
Responsável por monitorar transações em tempo real
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any
from web3 import Web3
from web3.exceptions import Web3Exception
import json

from config.settings import settings
from data.models import TransactionData, TransactionType
from interfaces.fraud_detection import IBlockchainMonitor

logger = logging.getLogger(__name__)

class EthereumMonitor(IBlockchainMonitor):
    """
    Monitor de transações da blockchain Ethereum
    
    Funcionalidades:
    - Monitoramento em tempo real de novos blocos
    - Filtragem de transações relevantes
    - Parsing de dados de transação
    - Callback para processamento de fraude
    """
    
    def __init__(self, callback_handler: Optional[Callable] = None):
        self.web3 = None
        self.callback_handler = callback_handler
        self.is_monitoring = False
        self.last_block_number = 0
        self.monitored_addresses = set()
        self.monitored_tokens = set(settings.supported_tokens.values())
        
        # Estatísticas
        self.stats = {
            "blocks_processed": 0,
            "transactions_processed": 0,
            "relevant_transactions": 0,
            "errors": 0,
            "start_time": None
        }
        
        logger.info("EthereumMonitor initialized")
    
    async def initialize(self):
        """Inicializa conexão com a blockchain"""
        try:
            # Conectar ao provider Ethereum
            self.web3 = Web3(Web3.HTTPProvider(settings.blockchain.ethereum_rpc_url))
            
            # Verificar conexão
            if not self.web3.is_connected():
                raise ConnectionError("Failed to connect to Ethereum node")
            
            # Obter último bloco
            latest_block = self.web3.eth.get_block('latest')
            self.last_block_number = latest_block['number']
            
            logger.info(f"Connected to Ethereum network. Latest block: {self.last_block_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Ethereum connection: {e}")
            return False
    
    async def start_monitoring(self):
        """Inicia monitoramento de transações"""
        if not self.web3:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize Ethereum connection")
        
        self.is_monitoring = True
        self.stats["start_time"] = datetime.utcnow()
        
        logger.info("Starting blockchain monitoring...")
        
        try:
            while self.is_monitoring:
                await self._process_new_blocks()
                await asyncio.sleep(settings.blockchain.block_confirmation)
                
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            self.stats["errors"] += 1
        finally:
            self.is_monitoring = False
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.is_monitoring = False
        logger.info("Stopping blockchain monitoring...")
    
    async def _process_new_blocks(self):
        """Processa novos blocos"""
        try:
            latest_block_number = self.web3.eth.get_block('latest')['number']
            
            # Processar blocos perdidos
            for block_number in range(self.last_block_number + 1, latest_block_number + 1):
                await self._process_block(block_number)
                self.stats["blocks_processed"] += 1
            
            self.last_block_number = latest_block_number
            
        except Web3Exception as e:
            logger.error(f"Web3 error processing blocks: {e}")
            self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"Unexpected error processing blocks: {e}")
            self.stats["errors"] += 1
    
    async def _process_block(self, block_number: int):
        """Processa um bloco específico"""
        try:
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            
            logger.debug(f"Processing block {block_number} with {len(block['transactions'])} transactions")
            
            for tx in block['transactions']:
                await self._process_transaction(tx, block)
                self.stats["transactions_processed"] += 1
                
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
            self.stats["errors"] += 1
    
    async def _process_transaction(self, tx_hash_or_dict, block):
        """Processa uma transação"""
        try:
            # Se recebemos hash, buscar dados completos
            if isinstance(tx_hash_or_dict, str):
                tx = self.web3.eth.get_transaction(tx_hash_or_dict)
            else:
                tx = tx_hash_or_dict
            
            # Verificar se é transação relevante
            if not self._is_relevant_transaction(tx):
                return
            
            # Converter para formato interno
            transaction_data = await self._parse_transaction(tx, block)
            
            if transaction_data:
                self.stats["relevant_transactions"] += 1
                
                # Executar callback se definido
                if self.callback_handler:
                    await self.callback_handler(transaction_data)
                
                logger.debug(f"Processed relevant transaction: {tx['hash'].hex()[:10]}...")
            
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            self.stats["errors"] += 1
    
    def _is_relevant_transaction(self, tx) -> bool:
        """Verifica se a transação é relevante para monitoramento"""
        
        # Verificar se envolve endereços monitorados
        if self.monitored_addresses:
            if (tx['from'] in self.monitored_addresses or 
                (tx['to'] and tx['to'] in self.monitored_addresses)):
                return True
        
        # Verificar se é transação de alto valor
        value_eth = self.web3.from_wei(tx['value'], 'ether')
        if value_eth > 100:  # > 100 ETH
            return True
        
        # Verificar se é interação com tokens monitorados
        if tx['to'] in self.monitored_tokens:
            return True
        
        # Verificar se é transação com gas price suspeito
        gas_price_gwei = self.web3.from_wei(tx['gasPrice'], 'gwei')
        if gas_price_gwei > settings.blockchain.gas_price_threshold:
            return True
        
        return False
    
    async def _parse_transaction(self, tx, block) -> Optional[TransactionData]:
        """Converte transação Ethereum para formato interno"""
        try:
            # Obter receipt para dados adicionais
            receipt = self.web3.eth.get_transaction_receipt(tx['hash'])
            
            # Determinar tipo de transação
            tx_type = self._determine_transaction_type(tx, receipt)
            
            # Dados básicos
            transaction_data = TransactionData(
                hash=tx['hash'].hex(),
                from_address=tx['from'],
                to_address=tx['to'],
                value=float(self.web3.from_wei(tx['value'], 'ether')),  # Converter para ETH
                gas_price=float(self.web3.from_wei(tx['gasPrice'], 'gwei')),  # Converter para Gwei
                timestamp=datetime.fromtimestamp(block['timestamp']),
                block_number=tx['blockNumber'],
                transaction_type=tx_type
            )
            
            # Dados específicos de tokens se aplicável
            if tx_type in [TransactionType.TRANSFER, TransactionType.SWAP]:
                token_data = await self._parse_token_data(tx, receipt)
                if token_data:
                    transaction_data.token_address = token_data.get('address')
                    transaction_data.token_amount = token_data.get('amount')
            
            # Contexto adicional
            transaction_data.context = {
                "gas_limit": tx['gas'],
                "gas_used": receipt['gasUsed'],
                "transaction_index": tx['transactionIndex'],
                "input_data_size": len(tx['input']) if tx['input'] else 0,
                "status": receipt['status']  # 1 = success, 0 = failed
            }
            
            return transaction_data
            
        except Exception as e:
            logger.error(f"Error parsing transaction {tx['hash'].hex()}: {e}")
            return None
    
    def _determine_transaction_type(self, tx, receipt) -> TransactionType:
        """Determina o tipo da transação"""
        
        # Transação falhada
        if receipt['status'] == 0:
            return TransactionType.CONTRACT_INTERACTION
        
        # Transação simples ETH
        if not tx['to'] or len(tx['input']) <= 2:
            return TransactionType.TRANSFER
        
        # Analisar input data para determinar tipo
        input_data = tx['input'].hex() if tx['input'] else ""
        
        # Métodos ERC20 comuns
        if input_data.startswith('0xa9059cbb'):  # transfer(address,uint256)
            return TransactionType.TRANSFER
        elif input_data.startswith('0x095ea7b3'):  # approve(address,uint256)
            return TransactionType.APPROVAL
        elif input_data.startswith('0x40c10f19'):  # mint(address,uint256)
            return TransactionType.MINT
        elif input_data.startswith('0x42966c68'):  # burn(uint256)
            return TransactionType.BURN
        
        # Métodos de DEX (swap)
        elif any(method in input_data for method in ['swapExact', 'swapTokens']):
            return TransactionType.SWAP
        
        # Default para interação com contrato
        return TransactionType.CONTRACT_INTERACTION
    
    async def _parse_token_data(self, tx, receipt) -> Optional[Dict[str, Any]]:
        """Extrai dados de tokens da transação"""
        try:
            # Analisar logs do receipt para eventos ERC20
            for log in receipt['logs']:
                # Event Transfer (index 0: from, index 1: to, data: value)
                if (len(log['topics']) >= 3 and 
                    log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'):
                    
                    # Decodificar valor do token
                    value_hex = log['data']
                    if value_hex and value_hex != '0x':
                        token_amount = int(value_hex, 16)
                        
                        return {
                            'address': log['address'],
                            'amount': float(token_amount / 10**18),  # Assumir 18 decimais
                            'from': '0x' + log['topics'][1].hex()[26:],  # Remove padding
                            'to': '0x' + log['topics'][2].hex()[26:]
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse token data: {e}")
            return None
    
    def add_monitored_address(self, address: str):
        """Adiciona endereço para monitoramento"""
        self.monitored_addresses.add(address.lower())
        logger.info(f"Added address to monitoring: {address}")
    
    def remove_monitored_address(self, address: str):
        """Remove endereço do monitoramento"""
        self.monitored_addresses.discard(address.lower())
        logger.info(f"Removed address from monitoring: {address}")
    
    def add_monitored_token(self, token_address: str):
        """Adiciona token para monitoramento"""
        self.monitored_tokens.add(token_address.lower())
        logger.info(f"Added token to monitoring: {token_address}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do monitor"""
        stats = self.stats.copy()
        
        if stats["start_time"]:
            uptime = (datetime.utcnow() - stats["start_time"]).total_seconds()
            stats["uptime_seconds"] = uptime
            stats["blocks_per_minute"] = (stats["blocks_processed"] / uptime * 60) if uptime > 0 else 0
            stats["transactions_per_minute"] = (stats["transactions_processed"] / uptime * 60) if uptime > 0 else 0
        
        stats["is_monitoring"] = self.is_monitoring
        stats["last_block_number"] = self.last_block_number
        stats["monitored_addresses_count"] = len(self.monitored_addresses)
        stats["monitored_tokens_count"] = len(self.monitored_tokens)
        
        return stats
    
    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[TransactionData]:
        """Busca transação específica por hash"""
        try:
            if not self.web3:
                await self.initialize()
            
            tx = self.web3.eth.get_transaction(tx_hash)
            block = self.web3.eth.get_block(tx['blockNumber'])
            
            return await self._parse_transaction(tx, block)
            
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_hash}: {e}")
            return None
