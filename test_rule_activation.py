#!/usr/bin/env python3
"""
🧪 ChimeraScan - Script de Teste de Ativação de Regras
=====================================================

Script automatizado para testar cada regra de detecção de fraudes individualmente.
Cada teste inclui:
- Função de geração de dados de teste específicos
- Função de chamada à API
- Função de análise e exibição dos resultados

Regras testadas:
1. Blacklist Interaction (CRITICAL)
2. High Value Transfer (HIGH) 
3. New Wallet Interaction (MEDIUM)
4. Suspicious Gas Price (LOW)
5. Unusual Time Pattern (MEDIUM)
6. Multiple Small Transfers (MEDIUM)
7. Wash Trading Pattern - Self-Trading (HIGH)
8. Wash Trading Pattern - Back-and-Forth (HIGH)
9. Wash Trading Pattern - Circular (HIGH)

Autor: ChimeraScan Team
Data: 2025-08-30
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import sys
import os

# Configurações
API_BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 30  # segundos


@dataclass 
class TestResult:
    """Resultado de um teste de regra"""
    rule_name: str
    success: bool
    triggered: bool
    error_message: str = ""
    api_response: Dict[str, Any] = None
    risk_score: float = 0.0
    alert_count: int = 0
    execution_time: float = 0.0


class RuleTestFramework:
    """Framework para testes automatizados de regras"""
    
    def __init__(self, api_url: str = API_BASE_URL):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.test_results: List[TestResult] = []
    
    def check_api_health(self) -> bool:
        """Verifica se a API está disponível"""
        try:
            print("🔍 Verificando saúde da API...")
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API está online - Status: {data.get('status', 'unknown')}")
                print(f"   Versão: {data.get('version', 'N/A')}")
                print(f"   Uptime: {data.get('uptime_seconds', 0):.1f}s")
                return True
            else:
                print(f"❌ API retornou status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Não foi possível conectar à API em {self.api_url}")
            print("   💡 Certifique-se de que a API está rodando: python start.py")
            return False
        except Exception as e:
            print(f"❌ Erro ao verificar API: {e}")
            return False
    
    def call_api(self, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Faz chamada para a API de análise"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/analyze/transaction",
                json=transaction_data,
                timeout=TEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erro na API: Status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Erro: {error_data.get('error', 'Erro desconhecido')}")
                except:
                    print(f"   Resposta: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout na API após {TEST_TIMEOUT}s")
            return None
        except Exception as e:
            print(f"❌ Erro na chamada da API: {e}")
            return None
    
    def analyze_response(self, response: Dict[str, Any], expected_rule: str) -> Dict[str, Any]:
        """Analisa a resposta da API"""
        analysis = {
            "triggered": False,
            "expected_rule_found": False,
            "risk_score": 0.0,
            "alert_count": 0,
            "triggered_rules": [],
            "alerts": []
        }
        
        if not response:
            return analysis
        
        # Extrair dados da análise
        analysis_result = response.get("analysis_result", {})
        analysis["triggered"] = analysis_result.get("is_suspicious", False)
        analysis["risk_score"] = analysis_result.get("risk_score", 0.0)
        analysis["triggered_rules"] = analysis_result.get("triggered_rules", [])
        
        # Extrair alertas
        alerts = response.get("alerts", [])
        analysis["alert_count"] = len(alerts)
        analysis["alerts"] = alerts
        
        # Verificar se a regra esperada foi ativada
        analysis["expected_rule_found"] = expected_rule in analysis["triggered_rules"]
        
        return analysis
    
    def display_test_result(self, test_result: TestResult, analysis: Dict[str, Any] = None):
        """Exibe resultado detalhado do teste"""
        print(f"\n{'='*80}")
        print(f"📊 RESULTADO DO TESTE: {test_result.rule_name.upper()}")
        print(f"{'='*80}")
        
        # Status geral
        status_icon = "✅" if test_result.success and test_result.triggered else "❌"
        print(f"{status_icon} Status: {'SUCESSO' if test_result.success else 'FALHA'}")
        print(f"🎯 Regra Ativada: {'SIM' if test_result.triggered else 'NÃO'}")
        print(f"⏱️  Tempo de Execução: {test_result.execution_time:.3f}s")
        
        if test_result.error_message:
            print(f"❌ Erro: {test_result.error_message}")
        
        if analysis:
            print(f"\n📈 MÉTRICAS DE ANÁLISE:")
            print(f"   Risk Score: {analysis['risk_score']:.3f}")
            print(f"   Total de Alertas: {analysis['alert_count']}")
            print(f"   Regras Ativadas: {', '.join(analysis['triggered_rules']) if analysis['triggered_rules'] else 'Nenhuma'}")
            
            # Debug adicional para regras específicas
            if test_result.rule_name == "suspicious_gas_price":
                print(f"\n🔧 DEBUG GAS PRICE:")
                if test_result.api_response and 'context' in test_result.api_response:
                    context = test_result.api_response['context']
                    print(f"   Gas Price Ratio: {context.get('gas_price_ratio', 'N/A'):.2f}")
                    print(f"   Transaction Gas: {context.get('transaction_gas_price', 'N/A')} Gwei")
                    print(f"   Average Gas: {context.get('average_gas_price', 'N/A')} Gwei")
                    
            elif test_result.rule_name == "unusual_time_pattern":
                print(f"\n🔧 DEBUG TIME PATTERN:")
                if test_result.api_response and 'context' in test_result.api_response:
                    context = test_result.api_response['context']
                    print(f"   Transaction Hour: {context.get('transaction_hour', 'N/A')}")
                    print(f"   Is Off Hours: {context.get('is_off_hours', 'N/A')}")
                    print(f"   Is Weekend: {context.get('is_weekend', 'N/A')}")
                    print(f"   Transaction Value: ${context.get('transaction_value', 0):,.2f}")
                # Debug dos alertas para verificar qual regra está gerando cada alerta
                if analysis and analysis['alerts']:
                    print(f"   Alertas por regra:")
                    for alert in analysis['alerts']:
                        rule_name = alert.get('rule_name', 'unknown')
                        severity = alert.get('severity', 'unknown')
                        print(f"     - {rule_name}: {severity}")
                        
            elif test_result.rule_name == "multiple_small_transfers":
                print(f"\n🔧 DEBUG MULTIPLE SMALL TRANSFERS:")
                if test_result.api_response and 'context' in test_result.api_response:
                    context = test_result.api_response['context']
                    print(f"   Transaction Value: ${context.get('individual_value', 0):,.2f}")
                    print(f"   Threshold: ${context.get('threshold', 9999):,.2f}")
                    print(f"   Pattern Type: {context.get('pattern_type', 'N/A')}")
                    print(f"   Analysis Method: {context.get('analysis_method', 'N/A')}")
                    if 'confidence_score' in context:
                        print(f"   Confidence Score: {context['confidence_score']:.1%}")
                    if 'pattern_indicators' in context:
                        indicators = context['pattern_indicators']
                        print(f"   Total Transactions: {indicators.get('total_transactions', 'N/A')}")
                        print(f"   Total Value: ${indicators.get('total_value', 0):,.2f}")
                        print(f"   Time Span: {indicators.get('time_span_minutes', 'N/A')} min")
            
            # Exibir alertas se existirem
            if analysis['alerts']:
                print(f"\n🚨 ALERTAS GERADOS:")
                for i, alert in enumerate(analysis['alerts'], 1):
                    severity = alert.get('severity', 'UNKNOWN')
                    title = alert.get('title', 'N/A')
                    description = alert.get('description', 'N/A')
                    
                    severity_icon = {
                        'LOW': '🟡',
                        'MEDIUM': '🟠', 
                        'HIGH': '🔴',
                        'CRITICAL': '🚫'
                    }.get(severity, '⚪')
                    
                    print(f"   {i}. {severity_icon} [{severity}] {title}")
                    print(f"      💬 {description}")
            elif test_result.triggered and analysis['alert_count'] == 0:
                print(f"\n⚠️  ATENÇÃO: Regra ativada mas nenhum alerta gerado!")
                print(f"   💡 Verifique se a configuração 'action' está definida como 'immediate_alert'")
        
        print(f"{'='*80}")
    
    # =================================================================
    # TESTES ESPECÍFICOS POR REGRA
    # =================================================================
    
    def test_blacklist_interaction(self) -> TestResult:
        """
        Teste 1: Blacklist Interaction (CRITICAL)
        Testa interação com endereço conhecido na blacklist
        """
        print(f"\n🧪 TESTE 1: BLACKLIST INTERACTION")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de endereço na blacklist")
        print("📋 Endereço de teste: 0x455bF23eA7575A537b6374953FA71B5F3653272c")
        
        start_time = time.time()
        
        # Dados de teste para ativar a regra blacklist
        transaction_data = {
            "hash": "0xtest001blacklist001test001blacklist001test001blacklist001test",
            "from_address": "0x455bF23eA7575A537b6374953FA71B5F3653272c",  # Endereço na blacklist
            "to_address": "0x1234567890123456789012345678901234567890",
            "value": 1000.0,  # Valor normal
            "gas_price": 25.0,  # Gas price normal
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_number": 18500000,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação com endereço blacklistado...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="blacklist_interaction",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "blacklist_interaction")
        
        return TestResult(
            rule_name="blacklist_interaction",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_high_value_transfer(self) -> TestResult:
        """
        Teste 2: High Value Transfer (HIGH)
        Testa detecção de transferência de alto valor (> $10,000)
        """
        print(f"\n🧪 TESTE 2: HIGH VALUE TRANSFER")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de transferência > $10,000")
        print("💰 Valor de teste: $50,000.00")
        
        start_time = time.time()
        
        # Criar timestamp para horário normal (14:00) para evitar ativar unusual_time_pattern
        now = datetime.now(timezone.utc)
        normal_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
        
        # Dados de teste para ativar a regra de alto valor
        transaction_data = {
            "hash": "0xtest002highvalue002test002highvalue002test002highvalue002",
            "from_address": "0x1111111111111111111111111111111111111111",
            "to_address": "0x2222222222222222222222222222222222222222", 
            "value": 50000.0,  # Valor alto para ativar a regra (> $10,000)
            "gas_price": 25.0,  # Gas price normal
            "timestamp": normal_time.isoformat(),  # Horário normal (14:00)
            "block_number": 18500001,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação de alto valor...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="high_value_transfer",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "high_value_transfer")
        
        return TestResult(
            rule_name="high_value_transfer",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_new_wallet_interaction(self) -> TestResult:
        """
        Teste 3: New Wallet Interaction (MEDIUM)
        Testa detecção de carteira muito nova (< 24h) com valor > $500
        """
        print(f"\n🧪 TESTE 3: NEW WALLET INTERACTION")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de carteira nova (< 24h)")
        print("🆕 Idade da carteira: 2 horas atrás")
        print("💰 Valor: $1,000.00")
        
        start_time = time.time()
        
        # Data de funding muito recente (2 horas atrás)
        funding_date = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Dados de teste para ativar a regra de carteira nova
        transaction_data = {
            "hash": "0xtest003newwallet003test003newwallet003test003newwallet003",
            "from_address": "0x3333333333333333333333333333333333333333",
            "to_address": "0x4444444444444444444444444444444444444444",
            "value": 1000.0,  # Valor > $500 para ativar a regra
            "gas_price": 25.0,  # Gas price normal
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_number": 18500002,
            "transaction_type": "TRANSFER",
            "fundeddate_from": funding_date.isoformat()  # Carteira criada há 2 horas
        }
        
        print("📤 Enviando transação com carteira nova...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="new_wallet_interaction",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "new_wallet_interaction")
        
        return TestResult(
            rule_name="new_wallet_interaction",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_suspicious_gas_price(self) -> TestResult:
        """
        Teste 4: Suspicious Gas Price (LOW)
        Testa detecção de gas price muito alto (> 5x normal)
        Base: 25 Gwei, Alto: > 125 Gwei
        """
        print(f"\n🧪 TESTE 4: SUSPICIOUS GAS PRICE")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de gas price suspeito")
        print("⛽ Gas price normal: 25 Gwei")
        print("⛽ Gas price de teste: 150 Gwei (6x normal)")
        print("⛽ Threshold calculado: max(25 × 5, 100) = 125 Gwei")
        print("⛽ Esperado: 150 > 125 ✓ (deve ativar a regra)")
        
        start_time = time.time()
        
        # Dados de teste para ativar a regra de gas price suspeito
        transaction_data = {
            "hash": "0xtest004suspgas004test004suspgas004test004suspgas004test",
            "from_address": "0x5555555555555555555555555555555555555555",
            "to_address": "0x6666666666666666666666666666666666666666",
            "value": 500.0,  # Valor normal
            "gas_price": 200.0,  # Gas price muito alto (6x o normal de 25 Gwei)
            "timestamp": datetime.now(timezone.utc).replace(hour=14).isoformat(),  # Horário normal
            "block_number": 18500003,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação com gas price suspeito...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="suspicious_gas_price",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "suspicious_gas_price")
        
        return TestResult(
            rule_name="suspicious_gas_price",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_unusual_time_pattern(self) -> TestResult:
        """
        Teste 5: Unusual Time Pattern (MEDIUM)
        Testa detecção de transação em horário suspeito (madrugada)
        com valor > $50,000
        """
        print(f"\n🧪 TESTE 5: UNUSUAL TIME PATTERN")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de horário suspeito")
        print("🕐 Horário: 03:00 (madrugada - off hours)")
        print("💰 Valor: $55,000.00 (minimamente acima do threshold)")
        print("📋 Threshold: $50,000 para ativar a regra")
        print("🕐 Off Hours: 22:00-06:00")
        
        start_time = time.time()
        
        # Criar timestamp para 03:00 da madrugada (horário suspeito)
        now = datetime.now(timezone.utc)
        suspicious_time = now.replace(hour=3, minute=0, second=0, microsecond=0)
        
        # Dados de teste para ativar a regra de horário suspeito
        transaction_data = {
            "hash": "0xtest005timepattern005test005timepattern005test005timepa",
            "from_address": "0x7777777777777777777777777777777777777777",
            "to_address": "0x8888888888888888888888888888888888888888",
            "value": 55000.0,  # Valor minimamente acima do threshold de $50,000
            "gas_price": 25.0,  # Gas price normal
            "timestamp": suspicious_time.isoformat(),  # Horário suspeito (03:00)
            "block_number": 18500004,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação em horário suspeito...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="unusual_time_pattern",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "unusual_time_pattern")
        
        return TestResult(
            rule_name="unusual_time_pattern",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_multiple_small_transfers(self) -> TestResult:
        """
        Teste 6: Multiple Small Transfers (MEDIUM)
        Testa detecção de padrão de estruturação/smurfing
        com múltiplas transferências pequenas
        """
        print(f"\n🧪 TESTE 6: MULTIPLE SMALL TRANSFERS")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de padrão de estruturação")
        print("💰 Valor de teste: $8,500.00 (abaixo do threshold de $9,999)")
        print("🔍 Endereço especial que simula padrão de estruturação")
        print("📋 Threshold: Transações < $9,999 são suspeitas se em padrão")
        
        start_time = time.time()
        
        # Dados de teste para ativar a regra de estruturação
        transaction_data = {
            "hash": "0xtest006structuring006test006structuring006test006struct",
            "from_address": "0xstructuring1234567890abcdef1234567890abcdef",  # Endereço que simula estruturação
            "to_address": "0x9999999999999999999999999999999999999999",
            "value": 8500.0,  # Valor abaixo do threshold ($9,999) - suspeito
            "gas_price": 25.0,  # Gas price normal
            "timestamp": datetime.now(timezone.utc).replace(hour=14).isoformat(),  # Horário normal
            "block_number": 18500005,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação com padrão de estruturação...")
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="multiple_small_transfers",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "multiple_small_transfers")
        
        return TestResult(
            rule_name="multiple_small_transfers",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_wash_trading_pattern(self) -> TestResult:
        """
        Teste 7: Wash Trading Pattern (HIGH)
        Testa detecção de padrões de wash trading suspeitos
        """
        print(f"\n🧪 TESTE 7: WASH TRADING PATTERN")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção de padrões de wash trading")
        print("📋 Cenário: Self-trading (endereço enviando para si mesmo)")
        
        start_time = time.time()
        
        # Dados de teste para ativar wash trading (self-trading)
        transaction_data = {
            "hash": "0xwash001trading001test001pattern001detection001wash001trading",
            "from_address": "0x1111222233334444555566667777888899990000",  # Mesmo endereço
            "to_address": "0x1111222233334444555566667777888899990000",    # que destino (self-trading)
            "value": 5000.0,  # Valor alto para chamar atenção
            "gas_price": 45.0,  # Gas price normal
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_number": 18600000,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação self-trading...")
        print(f"📊 From: {transaction_data['from_address'][:10]}...")
        print(f"📊 To:   {transaction_data['to_address'][:10]}... (MESMO ENDEREÇO)")
        print(f"💰 Valor: ${transaction_data['value']:,.2f}")
        
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="wash_trading_pattern",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "wash_trading_pattern")
        
        # Informações adicionais para wash trading
        print(f"🔍 Análise de resposta:")
        if response.get('result', {}).get('patterns_found'):
            patterns = response['result']['patterns_found']
            print(f"   📊 Padrões detectados: {len(patterns)}")
            for pattern in patterns[:3]:  # Mostrar até 3 padrões
                pattern_type = pattern.get('pattern_type', 'N/A')
                confidence = pattern.get('confidence_score', 0)
                print(f"   🎯 Tipo: {pattern_type} | Confiança: {confidence:.2f}")
        
        if response.get('result', {}).get('analysis_details'):
            details = response['result']['analysis_details']
            if 'statistical_analysis' in details:
                stat_info = details['statistical_analysis']
                print(f"   🧠 Análise Estatística: {stat_info.get('analysis_type', 'N/A')}")
                print(f"   📈 Score Estatístico: {stat_info.get('stat_score', 0):.2f}")
        
        return TestResult(
            rule_name="wash_trading_pattern",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_wash_trading_back_forth(self) -> TestResult:
        """
        Teste 8: Wash Trading Back-and-Forth Pattern (HIGH) - REFACTORED
        Testa detecção usando arquitetura refatorada com dados realistas
        """
        print(f"\n🧪 TESTE 8: WASH TRADING BACK-AND-FORTH (REFACTORED)")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção com arquitetura SOLID")
        print("📋 Cenário: Usar endereço que gerará padrão back-and-forth realista")
        
        start_time = time.time()
        
        # Usar endereço que o TestTransactionDataSource reconhece como back-and-forth
        transaction_data = {
            "hash": "0xrefactored001backforth001solid001architecture001test",
            "from_address": "0xAAAABBBBCCCCDDDDEEEEFFFF0000111122223333",  # Endereço com padrão AAAABBBB
            "to_address": "0xFFFFEEEEDDDDCCCCBBBBAAAA3333222211110000",    # Parceiro automático
            "value": 7500.0,  # Valor que não conflita com outras regras
            "gas_price": 35.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_number": 18700000,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação para análise refatorada...")
        print(f"📊 From: {transaction_data['from_address'][:16]}... (padrão AAAABBBB)")
        print(f"📊 To:   {transaction_data['to_address'][:16]}... (padrão FFFFEEEE)")
        print(f"💰 Valor: ${transaction_data['value']:,.2f}")
        print("🏗️ Usando arquitetura SOLID refatorada...")
        
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="wash_trading_back_forth_refactored",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "wash_trading_pattern")
        
        # Informações específicas para back-and-forth refatorado
        print(f"🔍 Análise arquitetura refatorada:")
        if response.get('result', {}).get('patterns_found'):
            patterns = response['result']['patterns_found']
            print(f"   📊 Padrões detectados: {len(patterns)}")
            for pattern in patterns[:3]:
                pattern_type = pattern.get('pattern_type', 'N/A')
                confidence = pattern.get('confidence_score', 0)
                print(f"   🎯 Tipo: {pattern_type} | Confiança: {confidence:.3f}")
                if pattern_type == 'BACK_AND_FORTH':
                    print(f"   ✅ BACK_AND_FORTH detectado via SOLID!")
        
        if response.get('result', {}).get('analysis_details'):
            details = response['result']['analysis_details']
            print(f"   🏗️ Algorithm: {details.get('algorithm_used', 'N/A')}")
            print(f"   📈 Patterns analyzed: {details.get('patterns_analyzed', 0)}")
        
        return TestResult(
            rule_name="wash_trading_back_forth_refactored",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def test_wash_trading_circular(self) -> TestResult:
        """
        Teste 9: Wash Trading Circular Pattern (HIGH) - REFACTORED
        Testa detecção usando arquitetura refatorada com geração inteligente
        """
        print(f"\n🧪 TESTE 9: WASH TRADING CIRCULAR (REFACTORED)")
        print(f"{'='*60}")
        print("🎯 Objetivo: Verificar detecção circular com SOLID principles")
        print("📋 Cenário: Usar endereço que ativará padrão circular complexo")
        
        start_time = time.time()
        
        # Usar endereço que o TestTransactionDataSource reconhece como circular
        transaction_data = {
            "hash": "0xrefactored001circular001chain001detection001solid001test",
            "from_address": "0x1111222233334444555566667777888899990000",  # Padrão 1111 2222
            "to_address": "0x0000999988887777666655554444333322221111",    # Padrão reverso circular
            "value": 12500.0,  # Valor que permite análise circular
            "gas_price": 42.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_number": 18800000,
            "transaction_type": "TRANSFER"
        }
        
        print("📤 Enviando transação para análise circular refatorada...")
        print(f"📊 From: {transaction_data['from_address'][:16]}... (padrão 11112222)")
        print(f"📊 To:   {transaction_data['to_address'][:16]}... (padrão 00009999)")
        print(f"💰 Valor: ${transaction_data['value']:,.2f}")
        print("� Sistema gerará cadeia circular inteligente...")
        
        response = self.call_api(transaction_data)
        execution_time = time.time() - start_time
        
        if not response:
            return TestResult(
                rule_name="wash_trading_circular_refactored",
                success=False,
                triggered=False,
                error_message="Falha na chamada da API",
                execution_time=execution_time
            )
        
        analysis = self.analyze_response(response, "wash_trading_pattern")
        
        # Informações específicas para circular refatorado
        print(f"🔍 Análise arquitetura circular:")
        if response.get('result', {}).get('patterns_found'):
            patterns = response['result']['patterns_found']
            print(f"   📊 Padrões detectados: {len(patterns)}")
            for pattern in patterns[:3]:
                pattern_type = pattern.get('pattern_type', 'N/A')
                confidence = pattern.get('confidence_score', 0)
                print(f"   🎯 Tipo: {pattern_type} | Confiança: {confidence:.3f}")
                if pattern_type == 'CIRCULAR':
                    print(f"   🔄 CIRCULAR detectado via Strategy Pattern!")
                    # Informações adicionais sobre cadeia circular
                    if 'circular_path' in pattern:
                        path_info = pattern['circular_path']
                        print(f"      🌐 Tamanho da cadeia: {len(path_info.get('addresses', []))}")
                        print(f"      💰 Volume total: ${path_info.get('total_volume', 0):,.2f}")
        
        if response.get('result', {}).get('analysis_details'):
            details = response['result']['analysis_details']
            print(f"   🏗️ Algorithm: {details.get('algorithm_used', 'N/A')}")
            print(f"   🔄 Circular paths found: {details.get('circular_paths_found', 0)}")
            if details.get('factory_enhanced', False):
                print(f"   ⚡ Enhanced factory patterns used!")
        
        return TestResult(
            rule_name="wash_trading_circular_refactored",
            success=True,
            triggered=analysis["expected_rule_found"],
            api_response=response,
            risk_score=analysis["risk_score"],
            alert_count=analysis["alert_count"],
            execution_time=execution_time
        )
    
    def run_all_tests(self):
        """Executa todos os testes de regras"""
        print("🚀 INICIANDO TESTES AUTOMATIZADOS DE REGRAS")
        print("="*80)
        
        # Verificar API antes de iniciar
        if not self.check_api_health():
            print("\n❌ API não está disponível. Abortando testes.")
            return False
        
        # Lista de testes para executar
        tests = [
            ("1. Blacklist Interaction", self.test_blacklist_interaction),
            ("2. High Value Transfer", self.test_high_value_transfer),
            ("3. New Wallet Interaction", self.test_new_wallet_interaction),
            ("4. Suspicious Gas Price", self.test_suspicious_gas_price),
            ("5. Unusual Time Pattern", self.test_unusual_time_pattern),
            ("6. Multiple Small Transfers", self.test_multiple_small_transfers),
            ("7. Wash Trading Pattern (Self)", self.test_wash_trading_pattern),
            ("8. Wash Trading Back-and-Forth", self.test_wash_trading_back_forth),
            ("9. Wash Trading Circular", self.test_wash_trading_circular)
        ]
        
        print(f"\n📋 EXECUTANDO {len(tests)} TESTES...")
        
        # Executar cada teste
        for test_name, test_func in tests:
            print(f"\n{'🔬 ' + test_name}")
            try:
                result = test_func()
                self.test_results.append(result)
                
                # Analisar resposta se disponível
                analysis = None
                if result.api_response:
                    analysis = self.analyze_response(result.api_response, result.rule_name)
                
                self.display_test_result(result, analysis)
                
            except Exception as e:
                print(f"❌ Erro durante o teste {test_name}: {e}")
                self.test_results.append(TestResult(
                    rule_name=test_name.split(". ")[1].lower().replace(" ", "_"),
                    success=False,
                    triggered=False,
                    error_message=str(e)
                ))
        
        # Exibir relatório final
        self.display_final_report()
        
        return True
    
    def display_final_report(self):
        """Exibe relatório final dos testes"""
        print(f"\n{'🏁 RELATÓRIO FINAL DOS TESTES'}")
        print("="*80)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        triggered_rules = sum(1 for r in self.test_results if r.triggered)
        
        print(f"📊 ESTATÍSTICAS GERAIS:")
        print(f"   Total de testes: {total_tests}")
        print(f"   Testes executados com sucesso: {successful_tests}/{total_tests}")
        print(f"   Regras ativadas corretamente: {triggered_rules}/{total_tests}")
        print(f"   Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
        print(f"   Taxa de detecção: {(triggered_rules/total_tests)*100:.1f}%")
        
        print(f"\n📋 RESUMO POR TESTE:")
        for result in self.test_results:
            status_icon = "✅" if result.success and result.triggered else "❌"
            rule_icon = "🎯" if result.triggered else "⭕"
            
            print(f"   {status_icon} {result.rule_name.replace('_', ' ').title()}")
            print(f"      {rule_icon} Regra ativada: {'SIM' if result.triggered else 'NÃO'}")
            print(f"      ⏱️  Tempo: {result.execution_time:.3f}s")
            if result.risk_score > 0:
                print(f"      📈 Risk Score: {result.risk_score:.3f}")
            if result.alert_count > 0:
                print(f"      🚨 Alertas: {result.alert_count}")
            if result.error_message:
                print(f"      ❌ Erro: {result.error_message}")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        if triggered_rules == total_tests:
            print("   ✅ Todas as regras estão funcionando perfeitamente!")
            print("   ✅ Sistema de detecção está operacional.")
        else:
            print("   ⚠️  Algumas regras não foram ativadas conforme esperado.")
            print("   🔍 Verifique a configuração das regras em config/rules.json")
            print("   🔧 Considere ajustar os thresholds das regras não ativadas.")
        
        print("="*80)


def main():
    """Função principal"""
    print("🛡️ ChimeraScan - Teste de Ativação de Regras")
    print("============================================")
    print("Este script testa automaticamente todas as regras de detecção.")
    print("Certifique-se de que a API está rodando em http://localhost:5000")
    print()
    
    # Criar framework de testes
    framework = RuleTestFramework()
    
    # Executar testes
    try:
        framework.run_all_tests()
    except KeyboardInterrupt:
        print("\n🛑 Testes interrompidos pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante a execução dos testes: {e}")
    
    print("\n🏁 Testes finalizados!")


if __name__ == "__main__":
    main()
