"""
Dependency Injection Container
Manages creation and lifecycle of application components
"""
from typing import Dict, Any, Optional, TypeVar, Type
import logging

from interfaces.fraud_detection import (
    IRuleEngine, IRiskScorer, IAlertManager, IFraudDetector,
    IBlockchainMonitor, ITransactionRepository, IAlertRepository
)
from interfaces.data_providers import (
    ITransactionHistoryProvider, IMarketDataProvider
)

T = TypeVar('T')

logger = logging.getLogger(__name__)

class DIContainer:
    """
    Simple dependency injection container
    Manages singleton instances of application components
    """
    
    def __init__(self):
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, callable] = {}
        self._initialized = False
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a singleton implementation for an interface"""
        self._factories[interface] = implementation
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a pre-created instance"""
        self._instances[interface] = instance
    
    def get(self, interface: Type[T]) -> T:
        """Get instance of the requested interface"""
        # Return existing instance if available
        if interface in self._instances:
            return self._instances[interface]
        
        # Create new instance from factory
        if interface in self._factories:
            factory = self._factories[interface]
            
            # Create instance (with dependency injection if constructor supports it)
            try:
                instance = self._create_instance(factory)
                self._instances[interface] = instance
                logger.debug(f"Created instance of {interface.__name__}")
                return instance
            except Exception as e:
                logger.error(f"Failed to create instance of {interface.__name__}: {e}")
                raise
        
        raise ValueError(f"No registration found for {interface.__name__}")
    
    def _create_instance(self, factory: Type[T]) -> T:
        """Create instance using constructor injection where possible"""
        try:
            # Special handling for services that need dependency injection
            if hasattr(factory, '__init__'):
                import inspect
                sig = inspect.signature(factory.__init__)
                params = list(sig.parameters.keys())[1:]  # Skip 'self'
                
                # If constructor has parameters, try to inject dependencies
                if params:
                    args = []
                    for param_name in params:
                        # Look for matching registered interfaces
                        param_annotation = sig.parameters[param_name].annotation
                        if param_annotation in self._factories or param_annotation in self._instances:
                            args.append(self.get(param_annotation))
                        else:
                            # Try to find by name convention
                            if param_name == 'transaction_provider':
                                from interfaces.data_providers import ITransactionHistoryProvider
                                args.append(self.get(ITransactionHistoryProvider))
                            elif param_name == 'market_provider':
                                from interfaces.data_providers import IMarketDataProvider
                                args.append(self.get(IMarketDataProvider))
                            else:
                                logger.warning(f"Could not inject dependency for parameter: {param_name}")
                                break
                    
                    if len(args) == len(params):
                        return factory(*args)
            
            # Default: create instance without injection
            return factory()
            
        except Exception as e:
            logger.error(f"Could not create instance of {factory.__name__}: {e}")
            raise
    
    def initialize_defaults(self):
        """Initialize default implementations"""
        if self._initialized:
            return
        
        try:
            # Import implementations here to avoid circular imports
            from core.rule_engine import RuleEngine
            from core.risk_scorer import RiskScorer
            from alerts.alert_manager import AlertManager
            from core.fraud_detector import FraudDetector
            from blockchain.ethereum_monitor import EthereumMonitor
            from infrastructure.data_providers.transaction_history_provider import SimpleTransactionHistoryProvider
            from infrastructure.data_providers.market_data_provider import SimpleMarketDataProvider
            from core.domain_services.pattern_analysis import StructuringDetectionService
            from core.domain_services.wash_trading_detection import AdvancedWashTradingDetectionService
            
            # Import advanced components (Etapa 2)
            from infrastructure.graph.transaction_graph_provider import AdvancedTransactionGraphProvider
            from infrastructure.analyzers.advanced_pattern_analyzers import (
                AdvancedTemporalAnalyzer, AdvancedVolumeAnalyzer
            )
            from infrastructure.data_sources.test_transaction_data_source import TestTransactionDataSource
            from core.domain_services.refactored_wash_trading_service import RefactoredWashTradingDetectionService
            
            # Import interfaces
            from interfaces.wash_trading import (
                IWashTradingDetector, ITransactionGraphProvider,
                ITemporalPatternAnalyzer, IVolumeAnalyzer
            )
            from interfaces.data_sources import ITransactionDataSource
            
            # Register default implementations
            self.register_singleton(IRuleEngine, RuleEngine)
            self.register_singleton(IRiskScorer, RiskScorer)
            self.register_singleton(IAlertManager, AlertManager)
            self.register_singleton(IFraudDetector, FraudDetector)
            self.register_singleton(IBlockchainMonitor, EthereumMonitor)
            
            # Register new data providers
            self.register_singleton(ITransactionHistoryProvider, SimpleTransactionHistoryProvider)
            self.register_singleton(IMarketDataProvider, SimpleMarketDataProvider)
            
            # Register advanced wash trading components (Etapa 2 - Refactored)
            self.register_singleton(ITransactionDataSource, TestTransactionDataSource)
            self.register_singleton(ITransactionGraphProvider, AdvancedTransactionGraphProvider)
            self.register_singleton(ITemporalPatternAnalyzer, AdvancedTemporalAnalyzer)
            self.register_singleton(IVolumeAnalyzer, AdvancedVolumeAnalyzer)
            self.register_singleton(IWashTradingDetector, RefactoredWashTradingDetectionService)
            
            # Register domain services (using concrete class as key for now)
            self.register_singleton(StructuringDetectionService, StructuringDetectionService)
            self.register_singleton(AdvancedWashTradingDetectionService, AdvancedWashTradingDetectionService)
            self.register_singleton(RefactoredWashTradingDetectionService, RefactoredWashTradingDetectionService)
            
            self._initialized = True
            logger.info("DI Container initialized with default implementations and new services")
            
        except Exception as e:
            logger.error(f"Failed to initialize DI container: {e}")
            raise

# Global container instance
container = DIContainer()
