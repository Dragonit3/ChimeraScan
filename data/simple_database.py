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
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        """Save alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts 
                (transaction_hash, rule_name, severity, title, description, risk_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                alert_data.get('transaction_hash'),
                alert_data.get('rule_name'),
                alert_data.get('severity'),
                alert_data.get('title'),
                alert_data.get('description'),
                alert_data.get('risk_score', 0.0)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
    
    def get_statistics(self) -> Dict:
        """Get current statistics from database"""
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
            
            row = cursor.fetchone()
            
            # Get alert count
            cursor.execute('SELECT COUNT(*) FROM alerts')
            alerts_count = cursor.fetchone()[0]
            
            conn.close()
            
            total_analyzed = row[0] or 0
            suspicious_detected = row[1] or 0
            
            return {
                'total_analyzed': total_analyzed,
                'suspicious_detected': suspicious_detected,
                'alerts_generated': alerts_count,
                'average_risk_score': row[2] or 0.0,
                'total_risk_score': row[3] or 0.0,
                'detection_rate': (suspicious_detected / max(total_analyzed, 1)) * 100 if total_analyzed > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_analyzed': 0,
                'suspicious_detected': 0,
                'alerts_generated': 0,
                'average_risk_score': 0.0,
                'total_risk_score': 0.0,
                'detection_rate': 0.0
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
        """Get recent alerts"""
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
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []