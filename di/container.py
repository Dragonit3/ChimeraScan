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
            # For now, just create instances without injection to avoid issues
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
            
            # Register default implementations
            self.register_singleton(IRuleEngine, RuleEngine)
            self.register_singleton(IRiskScorer, RiskScorer)
            self.register_singleton(IAlertManager, AlertManager)
            self.register_singleton(IFraudDetector, FraudDetector)
            self.register_singleton(IBlockchainMonitor, EthereumMonitor)
            
            self._initialized = True
            logger.info("DI Container initialized with default implementations")
            
        except Exception as e:
            logger.error(f"Failed to initialize DI container: {e}")
            raise

# Global container instance
container = DIContainer()
