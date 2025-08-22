"""
Fraud Detection Interfaces
Define contracts for all fraud detection components
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from data.models import TransactionData, AlertData, RiskLevel

# Forward declarations to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.fraud_detector import DetectionResult
    from core.rule_engine import RuleResult

class IRuleEngine(ABC):
    """Interface for rule engines"""
    
    @abstractmethod
    async def evaluate_transaction(self, transaction: TransactionData) -> List['RuleResult']:
        """Evaluate a transaction against all active rules"""
        pass
    
    @abstractmethod
    def reload_rules(self) -> bool:
        """Reload rules configuration"""
        pass
    
    @abstractmethod
    def get_active_rules(self) -> List[str]:
        """Get list of active rule names"""
        pass

class IRiskScorer(ABC):
    """Interface for risk scoring systems"""
    
    @abstractmethod
    async def calculate_risk(self, transaction: TransactionData) -> float:
        """Calculate risk score for a transaction (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    async def get_risk_factors(self, transaction: TransactionData) -> Dict[str, Any]:
        """Get detailed risk factors for a transaction"""
        pass

class IAlertManager(ABC):
    """Interface for alert management systems"""
    
    @abstractmethod
    async def process_alert(self, alert: AlertData) -> bool:
        """Process and store an alert"""
        pass
    
    @abstractmethod
    async def get_recent_alerts(self, limit: int = 10) -> List[AlertData]:
        """Get recent alerts"""
        pass
    
    @abstractmethod
    async def start_processing(self) -> None:
        """Start alert processing"""
        pass

class IFraudDetector(ABC):
    """Interface for fraud detection systems"""
    
    @abstractmethod
    async def analyze_transaction(self, transaction: TransactionData) -> 'DetectionResult':
        """Analyze a transaction for fraud patterns"""
        pass
    
    @abstractmethod
    async def analyze_batch(self, transactions: List[TransactionData]) -> List['DetectionResult']:
        """Analyze multiple transactions efficiently"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        pass

class IBlockchainMonitor(ABC):
    """Interface for blockchain monitoring systems"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize blockchain connection"""
        pass
    
    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start monitoring blockchain"""
        pass
    
    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop monitoring blockchain"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        pass

class ITransactionRepository(ABC):
    """Interface for transaction data access"""
    
    @abstractmethod
    async def save(self, transaction: TransactionData) -> str:
        """Save a transaction and return its ID"""
        pass
    
    @abstractmethod
    async def get_by_hash(self, hash: str) -> Optional[TransactionData]:
        """Get transaction by hash"""
        pass
    
    @abstractmethod
    async def get_recent(self, limit: int = 100) -> List[TransactionData]:
        """Get recent transactions"""
        pass

class IAlertRepository(ABC):
    """Interface for alert data access"""
    
    @abstractmethod
    async def save(self, alert: AlertData) -> str:
        """Save an alert and return its ID"""
        pass
    
    @abstractmethod
    async def get_recent(self, limit: int = 50) -> List[AlertData]:
        """Get recent alerts"""
        pass
    
    @abstractmethod
    async def get_by_severity(self, severity: RiskLevel) -> List[AlertData]:
        """Get alerts by severity level"""
        pass
