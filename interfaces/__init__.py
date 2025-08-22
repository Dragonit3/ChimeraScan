"""
Interfaces for fraud detection system components
Implementing Dependency Inversion Principle
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from data.models import TransactionData, AlertData, RiskLevel
from core.fraud_detector import DetectionResult
from core.rule_engine import RuleResult
