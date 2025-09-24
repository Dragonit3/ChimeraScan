"""
Simple Database Manager for ChimeraScan
Using pure SQLite for simplicity
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleDatabase:
    """Simple SQLite database for ChimeraScan"""
    
    def __init__(self, db_path: str = "chimera_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with simple schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE,
                    from_address TEXT,
                    to_address TEXT,
                    value_eth REAL,
                    gas_price REAL,
                    block_number INTEGER,
                    timestamp TEXT,
                    is_suspicious INTEGER DEFAULT 0,
                    risk_score REAL DEFAULT 0.0,
                    triggered_rules TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_hash TEXT,
                    rule_name TEXT,
                    severity TEXT,
                    title TEXT,
                    description TEXT,
                    risk_score REAL,
                    wallet_address TEXT,
                    context_data TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT,
                    resolved_by TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Simple database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_transaction(self, transaction_data: Dict, analysis_result: Dict):
        """Save transaction and analysis result"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract data
            triggered_rules = json.dumps(analysis_result.get('triggered_rules', []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO transactions 
                (hash, from_address, to_address, value_eth, gas_price, block_number, 
                 timestamp, is_suspicious, risk_score, triggered_rules)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_data.get('hash'),
                transaction_data.get('from_address'),
                transaction_data.get('to_address'),
                transaction_data.get('value', 0) / 1e18,  # Convert wei to ETH
                transaction_data.get('gas_price', 0),
                transaction_data.get('block_number'),
                transaction_data.get('timestamp'),
                1 if analysis_result.get('is_suspicious', False) else 0,
                analysis_result.get('risk_score', 0.0),
                triggered_rules
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Transaction saved: {transaction_data.get('hash')}")
            
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
    
    def save_alert(self, alert_data: Dict):
        """Save alert with enhanced context data and duplicate prevention"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 🛡️ Verificar se já existe alerta idêntico (prevenção de duplicatas)
            cursor.execute('''
                SELECT id FROM alerts 
                WHERE transaction_hash = ? AND rule_name = ? AND severity = ?
                AND datetime(created_at) > datetime('now', '-1 minute')
            ''', (
                alert_data.get('transaction_hash'),
                alert_data.get('rule_name'),
                alert_data.get('severity')
            ))
            
            existing = cursor.fetchone()
            if existing:
                logger.warning(f"Duplicate alert prevented: {alert_data.get('rule_name')} for {alert_data.get('transaction_hash')}")
                conn.close()
                return existing[0]  # Retorna ID do alerta existente
            
            # Serializar context_data se presente
            context_json = None
            if alert_data.get('context_data'):
                context_json = json.dumps(alert_data['context_data'])
            
            cursor.execute('''
                INSERT INTO alerts 
                (transaction_hash, rule_name, severity, title, description, risk_score, 
                 wallet_address, context_data, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_data.get('transaction_hash'),
                alert_data.get('rule_name'),
                alert_data.get('severity'),
                alert_data.get('title'),
                alert_data.get('description'),
                alert_data.get('risk_score', 0.0),
                alert_data.get('wallet_address'),
                context_json,
                alert_data.get('status', 'active')
            ))
            
            alert_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
    
    def get_statistics(self) -> Dict:
        """Get current statistics from database including enhanced alert data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get transaction stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_analyzed,
                    SUM(CASE WHEN is_suspicious = 1 THEN 1 ELSE 0 END) as suspicious_detected,
                    AVG(risk_score) as average_risk_score,
                    SUM(risk_score) as total_risk_score
                FROM transactions
            ''')
            
            tx_row = cursor.fetchone()
            
            # Get enhanced alert stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_alerts,
                    COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_severity_alerts,
                    COUNT(CASE WHEN created_at >= datetime('now', '-1 hour') THEN 1 END) as alerts_last_hour
                FROM alerts
            ''')
            
            alert_row = cursor.fetchone()
            
            conn.close()
            
            total_analyzed = tx_row[0] or 0
            suspicious_detected = tx_row[1] or 0
            
            return {
                # Transaction stats
                'total_analyzed': total_analyzed,
                'suspicious_detected': suspicious_detected,
                'average_risk_score': tx_row[2] or 0.0,
                'total_risk_score': tx_row[3] or 0.0,
                'detection_rate': (suspicious_detected / max(total_analyzed, 1)) * 100 if total_analyzed > 0 else 0.0,
                
                # Enhanced alert stats
                'alerts_generated': alert_row[0] or 0,
                'active_alerts': alert_row[1] or 0,
                'high_severity_alerts': alert_row[2] or 0,
                'alerts_last_hour': alert_row[3] or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_analyzed': 0,
                'suspicious_detected': 0,
                'alerts_generated': 0,
                'average_risk_score': 0.0,
                'total_risk_score': 0.0,
                'detection_rate': 0.0,
                'active_alerts': 0,
                'high_severity_alerts': 0,
                'alerts_last_hour': 0
            }
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM transactions 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            transactions = []
            for row in rows:
                tx = dict(row)
                if tx['triggered_rules']:
                    tx['triggered_rules'] = json.loads(tx['triggered_rules'])
                transactions.append(tx)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts with context data"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM alerts 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alert = dict(row)
                # Deserializar context_data se presente
                if alert['context_data']:
                    try:
                        alert['context_data'] = json.loads(alert['context_data'])
                    except:
                        alert['context_data'] = {}
                else:
                    alert['context_data'] = {}
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def get_alerts_by_transaction(self, transaction_hash: str) -> List[Dict]:
        """Get all alerts for a specific transaction"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE transaction_hash = ?
                ORDER BY created_at DESC
            ''', (transaction_hash,))
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alert = dict(row)
                if alert['context_data']:
                    try:
                        alert['context_data'] = json.loads(alert['context_data'])
                    except:
                        alert['context_data'] = {}
                else:
                    alert['context_data'] = {}
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts for transaction {transaction_hash}: {e}")
            return []
    
    def update_alert_status(self, alert_id: int, status: str, resolved_by: str = None) -> bool:
        """Update alert status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status == 'resolved':
                cursor.execute('''
                    UPDATE alerts 
                    SET status = ?, resolved_at = CURRENT_TIMESTAMP, resolved_by = ?
                    WHERE id = ?
                ''', (status, resolved_by, alert_id))
            else:
                cursor.execute('''
                    UPDATE alerts 
                    SET status = ?
                    WHERE id = ?
                ''', (status, alert_id))
            
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
            return False
    
    def get_alert_statistics(self) -> Dict:
        """Get enhanced alert statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Estatísticas básicas
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_alerts,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_alerts,
                    COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_alerts,
                    COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_alerts,
                    COUNT(CASE WHEN created_at >= datetime('now', '-1 hour') THEN 1 END) as alerts_last_hour,
                    COUNT(CASE WHEN created_at >= datetime('now', '-1 day') THEN 1 END) as alerts_last_day
                FROM alerts
            ''')
            
            row = cursor.fetchone()
            
            # Alertas por regra
            cursor.execute('''
                SELECT rule_name, COUNT(*) as count
                FROM alerts
                GROUP BY rule_name
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            alerts_by_rule = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'total_alerts': row[0] or 0,
                'active_alerts': row[1] or 0,
                'resolved_alerts': row[2] or 0,
                'critical_alerts': row[3] or 0,
                'high_severity_alerts': row[4] or 0,
                'alerts_last_hour': row[5] or 0,
                'alerts_last_day': row[6] or 0,
                'alerts_by_rule': alerts_by_rule
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'resolved_alerts': 0,
                'critical_alerts': 0,
                'high_severity_alerts': 0,
                'alerts_last_hour': 0,
                'alerts_last_day': 0,
                'alerts_by_rule': {}
            }
    
    def clear_all_alerts(self) -> bool:
        """Clear all alerts from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM alerts')
            conn.commit()
            
            rows_deleted = cursor.rowcount
            conn.close()
            
            logger.info(f"Cleared {rows_deleted} alerts from database")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing alerts: {e}")
            return False
    
    def clear_all_transactions(self) -> bool:
        """Clear all transactions from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM transactions')
            conn.commit()
            
            rows_deleted = cursor.rowcount
            conn.close()
            
            logger.info(f"Cleared {rows_deleted} transactions from database")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing transactions: {e}")
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all alerts and transactions from database"""
        try:
            alerts_cleared = self.clear_all_alerts()
            transactions_cleared = self.clear_all_transactions()
            
            return alerts_cleared and transactions_cleared
            
        except Exception as e:
            logger.error(f"Error clearing all data: {e}")
            return False