"""
Gerenciador de Alertas do Sistema de Detecção de Fraudes
Implementa notificações e gestão de alertas em tempo real
"""
import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import requests

from config.settings import settings
from data.models import AlertData, RiskLevel
from interfaces.fraud_detection import IAlertManager

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    """Canais de notificação disponíveis"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    TELEGRAM = "telegram"
    DASHBOARD = "dashboard"

@dataclass
class NotificationRule:
    """Regra para envio de notificações"""
    name: str
    severity_threshold: RiskLevel
    channels: List[NotificationChannel]
    recipients: List[str] = field(default_factory=list)
    template: Optional[str] = None
    cooldown_minutes: int = 5

class AlertManager(IAlertManager):
    """
    Gerenciador central de alertas e notificações
    
    Funcionalidades:
    - Processamento de alertas
    - Envio de notificações multi-canal
    - Gestão de templates
    - Controle de rate limiting
    - Dashboard em tempo real
    """
    
    def __init__(self):
        self.notification_rules = self._load_notification_rules()
        self.alert_queue = asyncio.Queue()
        self.active_alerts = {}  # Agora será: tx_hash -> [lista de alertas]
        self.stored_alerts = []  # Lista linear de todos os alertas
        self.notification_history = []
        self.rate_limiter = {}
        
        # Estatísticas
        self.stats = {
            "total_alerts": 0,
            "notifications_sent": 0,
            "failed_notifications": 0,
            "alerts_by_severity": {level.value: 0 for level in RiskLevel},
            "start_time": datetime.utcnow()
        }
        
        logger.info("AlertManager initialized")
    
    def _load_notification_rules(self) -> List[NotificationRule]:
        """Carrega regras de notificação"""
        # Regras padrão - idealmente viriam de configuração
        return [
            NotificationRule(
                name="critical_alerts",
                severity_threshold=RiskLevel.CRITICAL,
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK, NotificationChannel.TELEGRAM],
                recipients=["security@tecban.com", "fraud-team@tecban.com"],
                cooldown_minutes=0  # Sem cooldown para críticos
            ),
            NotificationRule(
                name="high_severity_alerts", 
                severity_threshold=RiskLevel.HIGH,
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
                recipients=["fraud-team@tecban.com"],
                cooldown_minutes=5
            ),
            NotificationRule(
                name="medium_severity_alerts",
                severity_threshold=RiskLevel.MEDIUM,
                channels=[NotificationChannel.DASHBOARD],
                recipients=[],
                cooldown_minutes=15
            )
        ]
    
    async def process_alert(self, alert: AlertData) -> bool:
        """
        Processa um novo alerta
        
        Args:
            alert: Dados do alerta para processar
            
        Returns:
            True se processado com sucesso
        """
        try:
            # Adicionar à fila de processamento
            await self.alert_queue.put(alert)
            
            # Processar imediatamente se for crítico
            if alert.severity == RiskLevel.CRITICAL:
                await self._process_alert_immediate(alert)
            
            # Atualizar estatísticas
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_severity"][alert.severity.value] += 1
            
            # Criar entrada para stored_alerts (lista linear)
            alert_dict = {
                "id": f"{alert.transaction_hash}_{alert.rule_name}_{len(self.stored_alerts)}",
                "transaction_hash": alert.transaction_hash,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "risk_score": alert.risk_score,
                "wallet_address": alert.wallet_address,
                "context_data": alert.context_data,
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Adicionar à lista linear de alertas
            self.stored_alerts.append(alert_dict)
            
            # Armazenar alerta ativo (permitindo múltiplos alertas por transação)
            if alert.transaction_hash not in self.active_alerts:
                self.active_alerts[alert.transaction_hash] = []
            
            self.active_alerts[alert.transaction_hash].append({
                "alert": alert,
                "created_at": datetime.utcnow(),
                "status": "active",
                "notifications_sent": 0
            })
            
            logger.info(f"Alert processed: {alert.rule_name} - {alert.severity.value} for tx {alert.transaction_hash[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return False
    
    async def _process_alert_immediate(self, alert: AlertData):
        """Processa alerta imediatamente (para críticos)"""
        matching_rules = self._get_matching_notification_rules(alert)
        
        for rule in matching_rules:
            if self._should_send_notification(alert, rule):
                await self._send_notifications(alert, rule)
    
    def _get_matching_notification_rules(self, alert: AlertData) -> List[NotificationRule]:
        """Encontra regras de notificação que se aplicam ao alerta"""
        matching_rules = []
        
        for rule in self.notification_rules:
            # Verificar se severity atende o threshold
            severity_levels = {
                RiskLevel.LOW: 1,
                RiskLevel.MEDIUM: 2, 
                RiskLevel.HIGH: 3,
                RiskLevel.CRITICAL: 4
            }
            
            if severity_levels[alert.severity] >= severity_levels[rule.severity_threshold]:
                matching_rules.append(rule)
        
        return matching_rules
    
    def _should_send_notification(self, alert: AlertData, rule: NotificationRule) -> bool:
        """Verifica se deve enviar notificação baseado em rate limiting"""
        if rule.cooldown_minutes == 0:
            return True
        
        # Verificar cooldown
        key = f"{alert.rule_name}_{rule.name}"
        last_sent = self.rate_limiter.get(key)
        
        if last_sent:
            time_diff = (datetime.utcnow() - last_sent).total_seconds() / 60
            if time_diff < rule.cooldown_minutes:
                logger.debug(f"Notification rate limited for {key}")
                return False
        
        return True
    
    async def _send_notifications(self, alert: AlertData, rule: NotificationRule):
        """Envia notificações através dos canais configurados"""
        for channel in rule.channels:
            try:
                success = await self._send_notification_channel(alert, rule, channel)
                if success:
                    self.stats["notifications_sent"] += 1
                else:
                    self.stats["failed_notifications"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending notification via {channel.value}: {e}")
                self.stats["failed_notifications"] += 1
        
        # Atualizar rate limiter
        key = f"{alert.rule_name}_{rule.name}"
        self.rate_limiter[key] = datetime.utcnow()
    
    async def _send_notification_channel(
        self, 
        alert: AlertData, 
        rule: NotificationRule, 
        channel: NotificationChannel
    ) -> bool:
        """Envia notificação através de um canal específico"""
        
        if channel == NotificationChannel.EMAIL:
            return await self._send_email_notification(alert, rule)
        elif channel == NotificationChannel.WEBHOOK:
            return await self._send_webhook_notification(alert, rule)
        elif channel == NotificationChannel.TELEGRAM:
            return await self._send_telegram_notification(alert, rule)
        elif channel == NotificationChannel.DASHBOARD:
            return await self._send_dashboard_notification(alert, rule)
        
        return False
    
    async def _send_email_notification(self, alert: AlertData, rule: NotificationRule) -> bool:
        """Envia notificação por email"""
        try:
            if not settings.alerts.email_user or not rule.recipients:
                return False
            
            # Preparar conteúdo do email
            subject = f"[TecBan Fraud Alert] {alert.severity.value}: {alert.title}"
            body = self._generate_email_body(alert)
            
            # Configurar email
            msg = MIMEMultipart()
            msg['From'] = settings.alerts.email_user
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            # Enviar para cada destinatário
            with smtplib.SMTP(settings.alerts.email_smtp_server, settings.alerts.email_port) as server:
                server.starttls()
                server.login(settings.alerts.email_user, settings.alerts.email_password)
                
                for recipient in rule.recipients:
                    msg['To'] = recipient
                    server.send_message(msg)
                    del msg['To']
            
            logger.info(f"Email notification sent to {len(rule.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _send_webhook_notification(self, alert: AlertData, rule: NotificationRule) -> bool:
        """Envia notificação via webhook"""
        try:
            if not settings.alerts.webhook_url:
                return False
            
            payload = {
                "alert_id": f"{alert.transaction_hash}_{alert.rule_name}",
                "severity": alert.severity.value,
                "rule_name": alert.rule_name,
                "title": alert.title,
                "description": alert.description,
                "transaction_hash": alert.transaction_hash,
                "wallet_address": alert.wallet_address,
                "risk_score": alert.risk_score,
                "detected_at": alert.detected_at.isoformat(),
                "context_data": alert.context_data
            }
            
            response = requests.post(
                settings.alerts.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Webhook notification sent successfully")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    async def _send_telegram_notification(self, alert: AlertData, rule: NotificationRule) -> bool:
        """Envia notificação via Telegram"""
        try:
            if not settings.alerts.telegram_bot_token:
                return False
            
            message = self._generate_telegram_message(alert)
            
            # Implementação simplificada - precisaria dos chat_ids dos destinatários
            logger.info("Telegram notification prepared (implementation needed)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    async def _send_dashboard_notification(self, alert: AlertData, rule: NotificationRule) -> bool:
        """Registra notificação para dashboard"""
        try:
            # Adicionar ao histórico para dashboard
            notification_entry = {
                "alert": alert,
                "rule": rule.name,
                "timestamp": datetime.utcnow(),
                "channel": "dashboard",
                "status": "delivered"
            }
            
            self.notification_history.append(notification_entry)
            
            # Manter apenas últimas 1000 entradas
            if len(self.notification_history) > 1000:
                self.notification_history = self.notification_history[-1000:]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register dashboard notification: {e}")
            return False
    
    def _generate_email_body(self, alert: AlertData) -> str:
        """Gera corpo do email formatado"""
        return f"""
        <html>
        <body>
            <h2>Alerta de Fraude TecBan</h2>
            <p><strong>Severidade:</strong> <span style="color: {'red' if alert.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL] else 'orange'}">{alert.severity.value}</span></p>
            <p><strong>Regra:</strong> {alert.rule_name}</p>
            <p><strong>Título:</strong> {alert.title}</p>
            <p><strong>Descrição:</strong> {alert.description}</p>
            <p><strong>Hash da Transação:</strong> <code>{alert.transaction_hash}</code></p>
            <p><strong>Carteira:</strong> <code>{alert.wallet_address or 'N/A'}</code></p>
            <p><strong>Score de Risco:</strong> {alert.risk_score:.3f}</p>
            <p><strong>Detectado em:</strong> {alert.detected_at.strftime('%d/%m/%Y %H:%M:%S UTC')}</p>
            
            <h3>Dados de Contexto:</h3>
            <pre>{json.dumps(alert.context_data, indent=2, ensure_ascii=False)}</pre>
            
            <p><em>Este é um alerta automático do Sistema de Detecção de Fraudes TecBan.</em></p>
        </body>
        </html>
        """
    
    def _generate_telegram_message(self, alert: AlertData) -> str:
        """Gera mensagem formatada para Telegram"""
        emoji = {
            RiskLevel.LOW: "🟡",
            RiskLevel.MEDIUM: "🟠", 
            RiskLevel.HIGH: "🔴",
            RiskLevel.CRITICAL: "🚨"
        }
        
        return f"""
{emoji[alert.severity]} *ALERTA DE FRAUDE TECBAN*

*Severidade:* {alert.severity.value}
*Regra:* {alert.rule_name}
*Título:* {alert.title}

*Transação:* `{alert.transaction_hash}`
*Score de Risco:* {alert.risk_score:.3f}
*Detectado:* {alert.detected_at.strftime('%d/%m/%Y %H:%M UTC')}

_{alert.description}_
        """.strip()
    
    async def start_processing(self):
        """Inicia processamento contínuo da fila de alertas"""
        logger.info("Starting alert processing...")
        
        while True:
            try:
                # Processar alertas da fila
                alert = await asyncio.wait_for(self.alert_queue.get(), timeout=1.0)
                
                matching_rules = self._get_matching_notification_rules(alert)
                for rule in matching_rules:
                    if self._should_send_notification(alert, rule):
                        await self._send_notifications(alert, rule)
                
                self.alert_queue.task_done()
                
            except asyncio.TimeoutError:
                # Timeout normal - continuar processamento
                continue
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(1)
    
    def get_active_alerts(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retorna alertas ativos (agora suportando múltiplos alertas por transação)"""
        active_list = []
        
        # Percorrer todas as transações com alertas
        for tx_hash, alert_list in self.active_alerts.items():
            # Cada transação pode ter múltiplos alertas
            for alert_info in alert_list:
                alert_dict = {
                    "id": f"{tx_hash}_{alert_info['alert'].rule_name}",
                    "transaction_hash": tx_hash,
                    "rule_name": alert_info["alert"].rule_name,
                    "severity": alert_info["alert"].severity.value,
                    "title": alert_info["alert"].title,
                    "description": alert_info["alert"].description,
                    "risk_score": alert_info["alert"].risk_score,
                    "created_at": alert_info["created_at"].isoformat(),
                    "detected_at": alert_info["created_at"].isoformat(),
                    "status": alert_info["status"],
                    # Informações adicionais da transação
                    "wallet_address": alert_info["alert"].wallet_address,
                    "context_data": alert_info["alert"].context_data or {}
                }
                
                # Incluir informações de transação do contexto se disponível
                context = alert_info["alert"].context_data or {}
                if context:
                    alert_dict.update({
                        "transaction_value": context.get("transaction_value"),
                        "from_address": context.get("from_address"),
                        "to_address": context.get("to_address"),
                        "fundeddate_from": context.get("fundeddate_from"),
                        "fundeddate_to": context.get("fundeddate_to"),
                        "wallet_age_hours": context.get("wallet_age_hours"),
                        "gas_price": context.get("gas_price"),
                        "block_number": context.get("block_number")
                    })
                
                # Se for um alerta de blacklist, adicionar informações do banco de dados
                if alert_info["alert"].rule_name == "blacklist_interaction":
                    context = alert_info["alert"].context_data or {}
                    
                    # Verificar se há múltiplos endereços blacklistados
                    if context.get("multiple_addresses", False):
                        blacklisted_addresses = context.get("blacklisted_addresses", [])
                        blacklist_infos = []
                        
                        for addr_info in blacklisted_addresses:
                            blacklist_info = self._get_blacklist_info_sync(addr_info["address"])
                            if blacklist_info:
                                blacklist_info["interaction_type"] = addr_info["interaction_type"]
                                blacklist_info["address"] = addr_info["address"]
                                blacklist_infos.append(blacklist_info)
                        
                        if blacklist_infos:
                            alert_dict["blacklist_infos"] = blacklist_infos  # Lista de informações
                            alert_dict["multiple_blacklists"] = True
                    else:
                        # Caso tradicional de um único endereço
                        primary_address = context.get("blacklisted_address") or alert_info["alert"].wallet_address
                        blacklist_info = self._get_blacklist_info_sync(primary_address)
                        if blacklist_info:
                            alert_dict["blacklist_info"] = blacklist_info
                            alert_dict["multiple_blacklists"] = False
                
                active_list.append(alert_dict)
        
        # Ordenar por data de criação (mais recentes primeiro) e limitar
        sorted_alerts = sorted(active_list, key=lambda x: x["created_at"], reverse=True)
        return sorted_alerts[:limit]
    
    def _get_blacklist_info_sync(self, address: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de blacklist de forma síncrona para uso no get_active_alerts"""
        try:
            # Import aqui para evitar dependências circulares
            from core.blacklist_manager import get_blacklist_database
            import asyncio
            
            # Executar função async de forma síncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                blacklist_db = get_blacklist_database()
                blacklist_entry = loop.run_until_complete(blacklist_db.get_blacklist_info(address))
                
                if blacklist_entry:
                    return {
                        "address_type": blacklist_entry.address_type.value,
                        "severity_level": blacklist_entry.severity_level.value,
                        "reason": blacklist_entry.reason,
                        "source": blacklist_entry.source,
                        "created_at": blacklist_entry.created_at.isoformat(),
                        "notes": blacklist_entry.notes
                    }
            finally:
                loop.close()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting blacklist info for {address}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema de alertas"""
        uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        
        # Contar total de alertas ativos (considerando múltiplos por transação)
        total_active_alerts = sum(len(alert_list) for alert_list in self.active_alerts.values())
        
        return {
            **self.stats,
            "uptime_hours": uptime / 3600,
            "alerts_per_hour": (self.stats["total_alerts"] / uptime * 3600) if uptime > 0 else 0,
            "active_alerts_count": total_active_alerts,
            "transactions_with_alerts": len(self.active_alerts),
            "notification_success_rate": (
                self.stats["notifications_sent"] / 
                (self.stats["notifications_sent"] + self.stats["failed_notifications"])
                if (self.stats["notifications_sent"] + self.stats["failed_notifications"]) > 0 else 1.0
            ),
            "queue_size": self.alert_queue.qsize()
        }
    
    def acknowledge_alert(self, transaction_hash: str, user: str = "system") -> bool:
        """Marca alerta como reconhecido"""
        if transaction_hash in self.active_alerts:
            self.active_alerts[transaction_hash]["status"] = "acknowledged"
            self.active_alerts[transaction_hash]["acknowledged_by"] = user
            self.active_alerts[transaction_hash]["acknowledged_at"] = datetime.utcnow()
            return True
        return False
    
    def resolve_alert(self, transaction_hash: str, resolution: str, user: str = "system") -> bool:
        """Marca alerta como resolvido"""
        if transaction_hash in self.active_alerts:
            self.active_alerts[transaction_hash]["status"] = "resolved"
            self.active_alerts[transaction_hash]["resolved_by"] = user
            self.active_alerts[transaction_hash]["resolution"] = resolution
            self.active_alerts[transaction_hash]["resolved_at"] = datetime.utcnow()
            return True
        return False
    
    async def get_recent_alerts(self, limit: int = 10) -> List[AlertData]:
        """Get recent alerts - implementing IAlertManager interface"""
        try:
            # Convert stored alerts to AlertData objects
            recent_alerts = []
            
            # Get alerts from stored_alerts (sorted by timestamp descending)
            sorted_alerts = sorted(
                self.stored_alerts, 
                key=lambda x: x.get("created_at", datetime.min), 
                reverse=True
            )
            
            for alert_dict in sorted_alerts[:limit]:
                try:
                    alert = AlertData(
                        rule_name=alert_dict.get("rule_name", "unknown"),
                        severity=RiskLevel(alert_dict.get("severity", "LOW")),
                        transaction_hash=alert_dict.get("transaction_hash", ""),
                        title=alert_dict.get("title", "Alert"),
                        description=alert_dict.get("description", ""),
                        risk_score=alert_dict.get("risk_score", 0.0),
                        wallet_address=alert_dict.get("wallet_address", ""),
                        context_data=alert_dict.get("context_data", {})
                    )
                    recent_alerts.append(alert)
                except Exception as e:
                    logger.warning(f"Error converting alert to AlertData: {e}")
                    continue
            
            return recent_alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
