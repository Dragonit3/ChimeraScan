"""
Aplicação Principal do Sistema de Detecção de Fraudes TecBan
Integra todos os componentes seguindo princípios de arquitetura
"""
import asyncio
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, List, Any

from core.fraud_detector import FraudDetector
from data.models import TransactionData, TransactionType
from config.settings import settings

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Inicializar componentes principais
fraud_detector = FraudDetector()

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "fraud_detector": "operational",
            "rule_engine": "operational",
            "risk_scorer": "operational"
        }
    })

@app.route('/api/v1/analyze/transaction', methods=['POST'])
async def analyze_transaction():
    """
    Analisa uma transação em busca de fraudes
    
    Expected JSON payload:
    {
        "hash": "0x...",
        "from_address": "0x...",
        "to_address": "0x...",
        "value": 1000.0,
        "gas_price": 20.0,
        "timestamp": "2024-01-01T12:00:00Z",
        "block_number": 12345,
        "transaction_type": "TRANSFER",
        "token_address": "0x..." (optional),
        "token_amount": 100.0 (optional)
    }
    """
    try:
        # Validar dados de entrada
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400
        
        # Campos obrigatórios
        required_fields = ["hash", "from_address", "value", "gas_price", "timestamp", "block_number"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        # Criar objeto TransactionData
        transaction = TransactionData(
            hash=data["hash"],
            from_address=data["from_address"],
            to_address=data.get("to_address"),
            value=float(data["value"]),
            gas_price=float(data["gas_price"]),
            timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
            block_number=int(data["block_number"]),
            transaction_type=TransactionType(data.get("transaction_type", "TRANSFER")),
            token_address=data.get("token_address"),
            token_amount=float(data["token_amount"]) if data.get("token_amount") else None,
            fundeddate_from=datetime.fromisoformat(data["fundeddate_from"].replace('Z', '+00:00')) if data.get("fundeddate_from") else None,
            fundeddate_to=datetime.fromisoformat(data["fundeddate_to"].replace('Z', '+00:00')) if data.get("fundeddate_to") else None
        )
        
        # Analisar transação
        result = await fraud_detector.analyze_transaction(transaction)
        
        # Retornar resultado
        response = {
            "transaction_hash": transaction.hash,
            "analysis_result": {
                "is_suspicious": result.is_suspicious,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level.value,
                "triggered_rules": result.triggered_rules,
                "alert_count": len(result.alerts)
            },
            "alerts": [
                {
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "risk_score": alert.risk_score,
                    "detected_at": alert.detected_at.isoformat()
                }
                for alert in result.alerts
            ],
            "context": result.context,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error analyzing transaction: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/analyze/batch', methods=['POST'])
async def analyze_batch():
    """
    Analisa um lote de transações
    
    Expected JSON payload:
    {
        "transactions": [
            {transaction_data}, 
            {transaction_data}, 
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        if not data or "transactions" not in data:
            return jsonify({"error": "JSON payload with 'transactions' array required"}), 400
        
        transactions_data = data["transactions"]
        if not isinstance(transactions_data, list):
            return jsonify({"error": "transactions must be an array"}), 400
        
        if len(transactions_data) > 100:  # Limite de batch
            return jsonify({"error": "Batch size limited to 100 transactions"}), 400
        
        # Converter para objetos TransactionData
        transactions = []
        for i, tx_data in enumerate(transactions_data):
            try:
                transaction = TransactionData(
                    hash=tx_data["hash"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data.get("to_address"),
                    value=float(tx_data["value"]),
                    gas_price=float(tx_data["gas_price"]),
                    timestamp=datetime.fromisoformat(tx_data["timestamp"].replace('Z', '+00:00')),
                    block_number=int(tx_data["block_number"]),
                    transaction_type=TransactionType(tx_data.get("transaction_type", "TRANSFER")),
                    token_address=tx_data.get("token_address"),
                    token_amount=float(tx_data["token_amount"]) if tx_data.get("token_amount") else None
                )
                transactions.append(transaction)
            except (KeyError, ValueError) as e:
                return jsonify({"error": f"Invalid transaction data at index {i}: {str(e)}"}), 400
        
        # Analisar lote
        results = await fraud_detector.analyze_batch(transactions)
        
        # Compilar resposta
        response = {
            "batch_size": len(transactions),
            "results": [
                {
                    "transaction_hash": tx.hash,
                    "is_suspicious": result.is_suspicious,
                    "risk_score": result.risk_score,
                    "risk_level": result.risk_level.value,
                    "alert_count": len(result.alerts)
                }
                for tx, result in zip(transactions, results)
            ],
            "summary": {
                "total_analyzed": len(results),
                "suspicious_count": sum(1 for r in results if r.is_suspicious),
                "total_alerts": sum(len(r.alerts) for r in results),
                "avg_risk_score": sum(r.risk_score for r in results) / len(results) if results else 0
            },
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error analyzing batch: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas do sistema"""
    try:
        stats = fraud_detector.get_stats()
        
        response = {
            "detection_stats": stats,
            "system_info": {
                "uptime_hours": stats["uptime_hours"],
                "version": "1.0.0",
                "environment": "production" if not settings.debug else "development"
            },
            "configuration": {
                "detection_threshold": settings.detection.anomaly_detection_threshold,
                "high_value_threshold": settings.detection.high_value_threshold,
                "supported_tokens": list(settings.supported_tokens.keys())
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/rules', methods=['GET'])
def get_rules():
    """Retorna configuração atual das regras"""
    try:
        active_rules = fraud_detector.rule_engine.get_active_rules()
        
        rules_info = []
        for rule_name in active_rules:
            rule_config = fraud_detector.rule_engine.get_rule_config(rule_name)
            if rule_config:
                rules_info.append({
                    "name": rule_name,
                    "enabled": rule_config.get("enabled", False),
                    "severity": rule_config.get("severity", "MEDIUM"),
                    "description": rule_config.get("description", ""),
                    "action": rule_config.get("action", "review_required")
                })
        
        return jsonify({
            "active_rules": rules_info,
            "total_rules": len(rules_info)
        })
        
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/rules/reload', methods=['POST'])
def reload_rules():
    """Recarrega configuração de regras"""
    try:
        fraud_detector.rule_engine.reload_rules()
        return jsonify({
            "status": "success",
            "message": "Rules reloaded successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error reloading rules: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handler para métodos não permitidos"""
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

def create_app():
    """Factory function para criar a aplicação"""
    return app

if __name__ == '__main__':
    logger.info("Starting ChimeraScan System")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Detection threshold: {settings.detection.anomaly_detection_threshold}")
    
    # Executar aplicação
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.debug
    )
