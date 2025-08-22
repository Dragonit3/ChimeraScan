"""
Aplicação Flask Completa do Sistema de Detecção de Fraudes TecBan
Integra todos os módulos e serve o dashboard web
"""
import asyncio
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import sys

# Adicionar path do projeto ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from di.container import container
from interfaces.fraud_detection import IFraudDetector, IAlertManager, IBlockchainMonitor
from data.models import TransactionData, TransactionType, AlertData
from config.settings import settings

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fraud_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__, 
           template_folder='dashboard/templates',
           static_folder='dashboard/static')

app.config['JSON_SORT_KEYS'] = False

# Componentes principais

# Estado da aplicação
app_state = {
    "initialized": False,
    "monitoring_active": False,
    "start_time": None,
    "errors": []
}

fraud_detector = None
blockchain_monitor = None
alert_manager = None

# Callback para processar transações da blockchain
async def process_blockchain_transaction(transaction: TransactionData):
    """
    Callback para processar transações da blockchain
    """
    try:
        # Analisar transação com detector de fraudes
        result = await fraud_detector.analyze_transaction(transaction)
        # Processar alertas se necessário
        for alert in result.alerts:
            await alert_manager.process_alert(alert)
        logger.debug(f"Processed blockchain transaction: {transaction.hash[:10]}...")
    except Exception as e:
        logger.error(f"Error processing blockchain transaction: {e}")

# Inicialização dos componentes (substitui @before_first_request)
import threading

def start_alert_processing():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(alert_manager.start_processing())

def initialize_components():
    global fraud_detector, blockchain_monitor, alert_manager
    try:
        logger.info("Initializing ChimeraScan System...")
        
        # Create instances directly for now (simplified DI)
        from core.fraud_detector import FraudDetector
        from alerts.alert_manager import AlertManager
        from blockchain.ethereum_monitor import EthereumMonitor
        
        fraud_detector = FraudDetector()
        alert_manager = AlertManager()
        blockchain_monitor = EthereumMonitor(callback_handler=process_blockchain_transaction)
        
        app_state["initialized"] = True
        app_state["start_time"] = datetime.utcnow()
        logger.info("All components initialized successfully")
        # Iniciar processamento de alertas em thread separada
        threading.Thread(target=start_alert_processing, daemon=True).start()
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        app_state["errors"].append(str(e))

initialize_components()


async def process_blockchain_transaction(transaction: TransactionData):
    """
    Callback para processar transações da blockchain
    """
    try:
        # Analisar transação com detector de fraudes
        result = await fraud_detector.analyze_transaction(transaction)
        
        # Processar alertas se necessário
        for alert in result.alerts:
            await alert_manager.process_alert(alert)
        
        logger.debug(f"Processed blockchain transaction: {transaction.hash[:10]}...")
        
    except Exception as e:
        logger.error(f"Error processing blockchain transaction: {e}")

# ========================================
# ROTAS DO DASHBOARD WEB
# ========================================

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos"""
    return send_from_directory('dashboard/static', filename)

# ========================================
# ROTAS DA API
# ========================================

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    # Sistema é considerado healthy se todos os componentes estão inicializados
    all_components_ready = fraud_detector and blockchain_monitor and alert_manager
    
    return jsonify({
        "status": "healthy" if all_components_ready else "initializing",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "fraud_detector": "operational" if fraud_detector else "initializing",
            "blockchain_monitor": "operational" if blockchain_monitor else "initializing",
            "alert_manager": "operational" if alert_manager else "initializing"
        },
        "monitoring_active": app_state["monitoring_active"],
        "uptime_seconds": (datetime.utcnow() - app_state["start_time"]).total_seconds() if app_state["start_time"] else 0,
        "errors": app_state["errors"][-5:]  # Últimos 5 erros
    })

@app.route('/api/v1/analyze/transaction', methods=['POST'])
def analyze_transaction():
    """
    Analisa uma transação em busca de fraudes
    """
    try:
        if not fraud_detector:
            return jsonify({"error": "System not initialized"}), 503
        
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
        
        # Analisar transação (síncronamente para API REST)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fraud_detector.analyze_transaction(transaction))
        
        # Processar alertas
        for alert in result.alerts:
            loop.run_until_complete(alert_manager.process_alert(alert))
        
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

@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas do sistema"""
    try:
        stats = {}
        
        # Estatísticas do detector de fraudes
        if fraud_detector:
            stats["detection_stats"] = fraud_detector.get_stats()
        
        # Estatísticas do monitor blockchain
        if blockchain_monitor:
            stats["blockchain_stats"] = blockchain_monitor.get_stats()
        
        # Estatísticas do gerenciador de alertas
        if alert_manager:
            stats["alert_stats"] = alert_manager.get_stats()
        
        # Informações do sistema
        stats["system_info"] = {
            "uptime_hours": (datetime.utcnow() - app_state["start_time"]).total_seconds() / 3600 if app_state["start_time"] else 0,
            "version": "1.0.0",
            "environment": "production" if not settings.debug else "development",
            "monitoring_active": app_state["monitoring_active"]
        }
        
        # Configurações
        stats["configuration"] = {
            "detection_threshold": settings.detection.anomaly_detection_threshold,
            "high_value_threshold": settings.detection.high_value_threshold,
            "supported_tokens": list(settings.supported_tokens.keys())
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/metrics/realtime', methods=['GET'])
def get_realtime_metrics():
    """Retorna métricas em tempo real para o dashboard"""
    try:
        start_time = app_state.get("start_time")
        if start_time:
            uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
            uptime_minutes = int(uptime_seconds / 60)
            logger.info(f"Uptime calculation: start_time={start_time}, now={datetime.utcnow()}, uptime_minutes={uptime_minutes}")
        else:
            uptime_seconds = 0
            uptime_minutes = 0
            logger.warning("start_time is None")
            
        # Estatísticas dos componentes
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_status": "healthy" if (fraud_detector and blockchain_monitor and alert_manager) else "initializing",
            "monitoring_active": app_state["monitoring_active"],
            "uptime_seconds": uptime_seconds,
            "uptime_minutes": uptime_minutes
        }
        
        # Estatísticas do detector de fraudes
        if fraud_detector:
            fraud_stats = fraud_detector.get_stats()
            
            # Calcular detection_rate baseado em suspicious_detected vs total_analyzed
            total_analyzed = fraud_stats.get("total_analyzed", 0)
            suspicious_detected = fraud_stats.get("suspicious_detected", 0)
            detection_rate = round((suspicious_detected / max(total_analyzed, 1)) * 100, 2) if total_analyzed > 0 else 0.0
            
            metrics.update({
                "transactions_analyzed": total_analyzed,
                "suspicious_detected": suspicious_detected,
                "total_alerts": fraud_stats.get("alerts_generated", 0),
                "detection_rate": detection_rate,
                "average_risk_score": fraud_stats.get("average_risk_score", 0.0)
            })
        else:
            metrics.update({
                "transactions_analyzed": 0,
                "suspicious_detected": 0,
                "total_alerts": 0,
                "detection_rate": 0.0,
                "average_risk_score": 0.0
            })
        
        # Estatísticas do gerenciador de alertas
        if alert_manager:
            alert_stats = alert_manager.get_stats()
            metrics.update({
                "active_alerts": alert_stats.get("active_alerts", 0),
                "alerts_last_hour": alert_stats.get("alerts_last_hour", 0),
                "high_severity_alerts": alert_stats.get("high_severity_alerts", 0),
                "alerts_generated": alert_stats.get("total_alerts", 0)  # Para compatibilidade
            })
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/rules', methods=['GET'])
def get_rules():
    """Retorna configuração atual das regras"""
    try:
        if not fraud_detector:
            return jsonify({"error": "System not initialized"}), 503
        
        # Obter regras ativas (implementadas)
        active_rules = fraud_detector.rule_engine.get_active_rules()
        
        # Obter todas as regras configuradas
        all_configured_rules = fraud_detector.rule_engine.get_all_configured_rules()
        
        rules_info = []
        for rule_name in all_configured_rules:
            rule_config = fraud_detector.rule_engine.get_rule_config(rule_name)
            if rule_config:
                # Verificar se está implementada
                is_implemented = rule_name in active_rules
                
                rules_info.append({
                    "name": rule_name,
                    "enabled": rule_config.get("enabled", False),
                    "implemented": is_implemented,
                    "status": "ACTIVE" if is_implemented else "CONFIGURED",
                    "severity": rule_config.get("severity", "MEDIUM"),
                    "description": rule_config.get("description", ""),
                    "action": rule_config.get("action", "review_required")
                })
        
        return jsonify({
            "active_rules": [rule for rule in rules_info if rule["implemented"]],
            "configured_rules": rules_info,
            "total_active": len(active_rules),
            "total_configured": len(all_configured_rules),
            "implementation_status": {
                "implemented": len(active_rules),
                "pending": len(all_configured_rules) - len(active_rules)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/alerts', methods=['GET'])
def get_alerts():
    """Retorna alertas ativos"""
    try:
        if not alert_manager:
            return jsonify({"error": "System not initialized"}), 503
        
        limit = request.args.get('limit', 50, type=int)
        alerts = alert_manager.get_active_alerts(limit)
        
        return jsonify({
            "alerts": alerts,
            "total": len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/monitoring/start', methods=['POST'])
def start_monitoring():
    """Inicia monitoramento da blockchain"""
    try:
        if not blockchain_monitor:
            return jsonify({"error": "System not initialized"}), 503
        
        if app_state["monitoring_active"]:
            return jsonify({"message": "Monitoring already active"}), 200
        
        # Iniciar monitoramento em thread separada
        def start_blockchain_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(blockchain_monitor.start_monitoring())
            
        threading.Thread(target=start_blockchain_monitoring, daemon=True).start()
        app_state["monitoring_active"] = True
        
        return jsonify({
            "status": "success",
            "message": "Blockchain monitoring started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Para monitoramento da blockchain"""
    try:
        if not blockchain_monitor:
            return jsonify({"error": "System not initialized"}), 503
        
        blockchain_monitor.stop_monitoring()
        app_state["monitoring_active"] = False
        
        return jsonify({
            "status": "success",
            "message": "Blockchain monitoring stopped",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/rules/reload', methods=['POST'])
def reload_rules():
    """Recarrega configuração de regras"""
    try:
        if not fraud_detector:
            return jsonify({"error": "System not initialized"}), 503
        
        fraud_detector.rule_engine.reload_rules()
        return jsonify({
            "status": "success",
            "message": "Rules reloaded successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error reloading rules: {e}")
        return jsonify({"error": "Internal server error"}), 500

# ========================================
# HANDLERS DE ERRO
# ========================================

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

# ========================================
# FUNÇÃO PRINCIPAL
# ========================================

def create_app():
    """Factory function para criar a aplicação"""
    return app

if __name__ == '__main__':
    logger.info("Starting ChimeraScan System")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Detection threshold: {settings.detection.anomaly_detection_threshold}")
    
    # Configurar loop de eventos para async
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Executar aplicação
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.debug,
        threaded=True
    )
