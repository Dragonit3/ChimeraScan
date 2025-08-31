"""
Simple Market Data Provider
Implementação básica para dados de mercado crypto
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from interfaces.data_providers import IMarketDataProvider

logger = logging.getLogger(__name__)


class SimpleMarketDataProvider(IMarketDataProvider):
    """
    Implementação simples de dados de mercado
    
    Responsabilidade: Fornecer cotações e dados de mercado para análise de valores
    Princípios: Interface Segregation, Dependency Inversion
    
    Nota: Implementação inicial que pode ser expandida para APIs reais
    (CoinGecko, CoinMarketCap, etc.) sem quebrar o contrato
    """
    
    def __init__(self):
        """Initialize simple provider with basic cache"""
        self._price_cache = {}  # symbol -> {price, timestamp}
        self._cache_duration = timedelta(minutes=2)  # Cache por 2 minutos
        
        # Preços simulados para desenvolvimento
        self._simulated_prices = {
            "ETH": 2500.00,
            "BTC": 45000.00,
            "USDT": 1.00,
            "USDC": 1.00,
            "DAI": 1.00,
            "WETH": 2500.00,
            "MATIC": 0.85,
            "LINK": 15.50,
            "UNI": 8.20,
            "AAVE": 110.00
        }
    
    async def get_token_price_usd(self, token_symbol: str) -> Optional[float]:
        """
        Retorna preço atual do token em USD
        
        Implementação inicial: usa preços simulados
        Futura: consultará APIs reais de cotação
        """
        try:
            # Verificar cache primeiro
            if self._is_price_cache_valid(token_symbol):
                return self._price_cache[token_symbol]["price"]
            
            # Obter preço (simulado por enquanto)
            price = self._get_simulated_price(token_symbol)
            
            if price is not None:
                # Cache o resultado
                self._price_cache[token_symbol] = {
                    "price": price,
                    "timestamp": datetime.utcnow()
                }
                
                logger.debug(f"Retrieved price for {token_symbol}: ${price:.2f}")
                return price
            
            logger.warning(f"No price found for token: {token_symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {token_symbol}: {e}")
            return None
    
    async def get_market_cap(self, token_symbol: str) -> Optional[float]:
        """
        Retorna market cap do token
        
        Implementação inicial: calcula baseado em supply simulado
        """
        try:
            price = await self.get_token_price_usd(token_symbol)
            if price is None:
                return None
            
            # Supply simulado para cálculo de market cap
            simulated_supplies = {
                "ETH": 120_000_000,
                "BTC": 19_500_000,
                "USDT": 80_000_000_000,
                "USDC": 50_000_000_000,
                "DAI": 5_000_000_000,
                "WETH": 3_000_000,
                "MATIC": 9_000_000_000,
                "LINK": 500_000_000,
                "UNI": 750_000_000,
                "AAVE": 16_000_000
            }
            
            supply = simulated_supplies.get(token_symbol.upper(), 1_000_000)
            market_cap = price * supply
            
            logger.debug(f"Market cap for {token_symbol}: ${market_cap:,.2f}")
            return market_cap
            
        except Exception as e:
            logger.error(f"Error calculating market cap for {token_symbol}: {e}")
            return None
    
    async def get_volume_24h(self, token_symbol: str) -> Optional[float]:
        """
        Retorna volume de 24h do token
        
        Implementação inicial: simula volume baseado no market cap
        """
        try:
            market_cap = await self.get_market_cap(token_symbol)
            if market_cap is None:
                return None
            
            # Volume típico é cerca de 5-15% do market cap por dia
            import random
            volume_ratio = random.uniform(0.05, 0.15)
            volume_24h = market_cap * volume_ratio
            
            logger.debug(f"24h volume for {token_symbol}: ${volume_24h:,.2f}")
            return volume_24h
            
        except Exception as e:
            logger.error(f"Error getting 24h volume for {token_symbol}: {e}")
            return None
    
    def _is_price_cache_valid(self, token_symbol: str) -> bool:
        """Verifica se cache de preço ainda é válido"""
        if token_symbol not in self._price_cache:
            return False
        
        cache_entry = self._price_cache[token_symbol]
        cache_time = cache_entry["timestamp"]
        
        return datetime.utcnow() - cache_time < self._cache_duration
    
    def _get_simulated_price(self, token_symbol: str) -> Optional[float]:
        """
        Obtém preço simulado com pequena variação
        
        Simula volatilidade real do mercado crypto
        """
        import random
        
        base_price = self._simulated_prices.get(token_symbol.upper())
        if base_price is None:
            return None
        
        # Adicionar volatilidade realista (±2-5%)
        volatility = random.uniform(-0.05, 0.05)
        current_price = base_price * (1 + volatility)
        
        return round(current_price, 2)
