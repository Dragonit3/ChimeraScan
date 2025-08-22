# 🏗️ Melhorias de Arquitetura Recomendadas

## 1. Implementar Dependency Injection

### Problema Atual
```python
# Hard dependencies dificultam testes e flexibilidade
class FraudDetector:
    def __init__(self):
        self.rule_engine = RuleEngine()  # Dependência hard-coded
        self.risk_scorer = RiskScorer()
```

### Solução Proposta
```python
# interfaces/fraud_detection.py
from abc import ABC, abstractmethod

class IRuleEngine(ABC):
    @abstractmethod
    async def evaluate_transaction(self, transaction: TransactionData) -> List[RuleResult]:
        pass

class IRiskScorer(ABC):
    @abstractmethod
    async def calculate_risk(self, transaction: TransactionData) -> float:
        pass

# core/fraud_detector.py
class FraudDetector:
    def __init__(self, rule_engine: IRuleEngine, risk_scorer: IRiskScorer):
        self.rule_engine = rule_engine
        self.risk_scorer = risk_scorer

# di_container.py
class Container:
    def __init__(self):
        self._rule_engine = RuleEngine()
        self._risk_scorer = RiskScorer()
        self._fraud_detector = FraudDetector(self._rule_engine, self._risk_scorer)
    
    def get_fraud_detector(self) -> FraudDetector:
        return self._fraud_detector
```

## 2. Sistema de Eventos (Observer Pattern)

### Problema Atual
- Acoplamento direto entre componentes
- Dificuldade para adicionar novos handlers

### Solução Proposta
```python
# events/event_bus.py
from typing import Dict, List, Callable
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    FRAUD_DETECTED = "fraud_detected"
    HIGH_RISK_TRANSACTION = "high_risk_transaction"
    ALERT_GENERATED = "alert_generated"

@dataclass
class Event:
    type: EventType
    data: Any
    timestamp: datetime

class EventBus:
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event: Event):
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                await handler(event)

# Usage
event_bus = EventBus()
event_bus.subscribe(EventType.FRAUD_DETECTED, alert_manager.handle_fraud)
event_bus.subscribe(EventType.FRAUD_DETECTED, metrics_service.update_stats)
```

## 3. CQRS (Command Query Responsibility Segregation)

### Problema Atual
- Write model (detecção) misturado com read model (dashboard)
- Métricas calculadas em tempo real

### Solução Proposta
```python
# commands/fraud_commands.py
@dataclass
class AnalyzeTransactionCommand:
    transaction: TransactionData
    
class FraudCommandHandler:
    async def handle(self, command: AnalyzeTransactionCommand) -> DetectionResult:
        # Lógica de detecção
        result = await self.fraud_detector.analyze_transaction(command.transaction)
        
        # Publish event
        await self.event_bus.publish(Event(
            type=EventType.FRAUD_DETECTED,
            data=result
        ))
        
        return result

# queries/dashboard_queries.py
@dataclass
class GetMetricsQuery:
    time_range: timedelta

class DashboardQueryHandler:
    async def handle(self, query: GetMetricsQuery) -> DashboardMetrics:
        # Read from optimized read model
        return await self.metrics_repository.get_metrics(query.time_range)
```

## 4. Strategy Pattern para Algoritmos de Detecção

### Problema Atual
- Algoritmos hard-coded no RiskScorer
- Dificulta troca de estratégias

### Solução Proposta
```python
# strategies/risk_strategies.py
class RiskStrategy(ABC):
    @abstractmethod
    async def calculate_risk(self, transaction: TransactionData) -> float:
        pass

class MLBasedRiskStrategy(RiskStrategy):
    async def calculate_risk(self, transaction: TransactionData) -> float:
        # ML-based calculation
        pass

class HeuristicRiskStrategy(RiskStrategy):
    async def calculate_risk(self, transaction: TransactionData) -> float:
        # Rule-based heuristic
        pass

class RiskScorer:
    def __init__(self, strategy: RiskStrategy):
        self.strategy = strategy
    
    async def calculate_risk(self, transaction: TransactionData) -> float:
        return await self.strategy.calculate_risk(transaction)
```

## 5. Circuit Breaker Pattern para APIs Externas

### Problema Atual
- Sem proteção contra falhas de APIs externas
- Poderia derrubar sistema inteiro

### Solução Proposta
```python
# resilience/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
infura_circuit_breaker = CircuitBreaker()

async def get_block_data_with_fallback(block_number):
    try:
        return await infura_circuit_breaker.call(
            web3.eth.get_block, block_number
        )
    except CircuitBreakerError:
        # Fallback to simulation
        return generate_simulated_block()
```

## 6. Repository Pattern para Data Access

### Problema Atual
- Acesso direto ao banco de dados espalhado
- Dificulta testes e troca de persistência

### Solução Proposta
```python
# repositories/interfaces.py
class ITransactionRepository(ABC):
    @abstractmethod
    async def save(self, transaction: TransactionData) -> str:
        pass
    
    @abstractmethod
    async def get_by_hash(self, hash: str) -> Optional[TransactionData]:
        pass

# repositories/sql_transaction_repository.py
class SQLTransactionRepository(ITransactionRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    async def save(self, transaction: TransactionData) -> str:
        # SQLAlchemy implementation
        pass

# repositories/in_memory_transaction_repository.py
class InMemoryTransactionRepository(ITransactionRepository):
    def __init__(self):
        self._transactions = {}
    
    async def save(self, transaction: TransactionData) -> str:
        # In-memory implementation for tests
        pass
```

## 7. Health Check System

### Problema Atual
- Health check básico
- Não verifica dependências externas

### Solução Proposta
```python
# health/health_checks.py
@dataclass
class HealthCheckResult:
    name: str
    status: str
    details: Dict[str, Any]
    duration_ms: float

class HealthCheckService:
    def __init__(self):
        self.checks = []
    
    def register_check(self, check: Callable):
        self.checks.append(check)
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        results = {}
        for check in self.checks:
            start = time.time()
            try:
                result = await check()
                duration = (time.time() - start) * 1000
                results[check.__name__] = HealthCheckResult(
                    name=check.__name__,
                    status="healthy",
                    details=result,
                    duration_ms=duration
                )
            except Exception as e:
                results[check.__name__] = HealthCheckResult(
                    name=check.__name__,
                    status="unhealthy",
                    details={"error": str(e)},
                    duration_ms=(time.time() - start) * 1000
                )
        return results

# Health checks
async def database_health_check():
    # Check database connectivity
    pass

async def blockchain_health_check():
    # Check blockchain API
    pass

# Register checks
health_service.register_check(database_health_check)
health_service.register_check(blockchain_health_check)
```

## 8. Improved Configuration Management

### Problema Atual
- Configurações espalhadas
- Sem validação de configuração

### Solução Proposta
```python
# config/configuration.py
from pydantic import BaseSettings, validator
from typing import Optional

class DatabaseConfig(BaseSettings):
    url: str
    pool_size: int = 20
    max_overflow: int = 30
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('postgresql://', 'sqlite://')):
            raise ValueError('Invalid database URL')
        return v

class BlockchainConfig(BaseSettings):
    ethereum_rpc_url: str
    etherscan_api_key: Optional[str] = None
    
    @validator('ethereum_rpc_url')
    def validate_rpc_url(cls, v):
        if not v.startswith('https://'):
            raise ValueError('RPC URL must use HTTPS')
        return v

class AppConfig(BaseSettings):
    database: DatabaseConfig
    blockchain: BlockchainConfig
    debug: bool = False
    
    class Config:
        env_nested_delimiter = '__'
        case_sensitive = False

# Usage
config = AppConfig(
    database=DatabaseConfig(),
    blockchain=BlockchainConfig()
)
```

## 9. Rate Limiting & Throttling

### Problema Atual
- Sem controle de rate limiting
- Pode sobrecarregar APIs externas

### Solução Proposta
```python
# middleware/rate_limiter.py
from asyncio import Semaphore
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, time_window: timedelta):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    async def acquire(self, key: str) -> bool:
        now = datetime.utcnow()
        window_start = now - self.time_window
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True

# Usage
api_rate_limiter = RateLimiter(max_requests=100, time_window=timedelta(minutes=1))

async def call_external_api(endpoint):
    if not await api_rate_limiter.acquire(endpoint):
        raise RateLimitError("Rate limit exceeded")
    
    return await http_client.get(endpoint)
```

## 10. Structured Logging & Observability

### Problema Atual
- Logs básicos
- Sem tracing distribuído

### Solução Proposta
```python
# observability/structured_logging.py
import structlog
from contextvars import ContextVar

# Context for request tracing
request_id_var: ContextVar[str] = ContextVar('request_id')

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
logger = structlog.get_logger()

async def analyze_transaction(transaction_data):
    request_id_var.set(str(uuid.uuid4()))
    
    logger.info(
        "Starting transaction analysis",
        transaction_hash=transaction_data.hash,
        transaction_value=transaction_data.value
    )
    
    # Analysis logic...
    
    logger.info(
        "Transaction analysis completed",
        risk_score=result.risk_score,
        suspicious=result.is_suspicious
    )
```

## Benefícios Esperados

1. **Testabilidade**: Dependency injection facilita unit tests
2. **Flexibilidade**: Strategy pattern permite trocar algoritmos
3. **Robustez**: Circuit breaker protege contra falhas
4. **Observabilidade**: Logs estruturados facilitam debugging
5. **Escalabilidade**: CQRS separa read/write loads
6. **Manutenibilidade**: Separação clara de responsabilidades

## Implementação Gradual

1. **Fase 1**: Implementar interfaces e dependency injection
2. **Fase 2**: Adicionar sistema de eventos
3. **Fase 3**: Implementar CQRS para métricas
4. **Fase 4**: Adicionar circuit breakers
5. **Fase 5**: Melhorar observabilidade

Esta abordagem gradual permite melhorar a arquitetura sem quebrar o sistema existente.
