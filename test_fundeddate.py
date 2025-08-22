#!/usr/bin/env python3
"""
Teste da nova funcionalidade fundeddate_from/fundeddate_to
"""
import requests
import json
from datetime import datetime, timedelta

# URL da API
BASE_URL = "http://localhost:5000"

def test_new_wallet_analysis():
    """Testa análise de carteira nova com fundeddate"""
    
    # Data atual simulada
    current_time = datetime.now()
    
    # Carteira criada há 12 horas (deve disparar alerta)
    funded_time = current_time - timedelta(hours=12)
    
    # Dados da transação com carteira nova
    transaction_data = {
        "hash": "0x1234567890abcdef1234567890abcdef12345678",
        "from_address": "0x742d35Cc631C0532925a3b8D33C9",
        "to_address": "0xF977814e90dA44bFA03b6295",
        "value": 5000.0,  # Acima do limite de $1000
        "gas_price": 25.0,
        "timestamp": current_time.isoformat() + "Z",
        "block_number": 23197704,
        "transaction_type": "TRANSFER",
        "fundeddate_from": funded_time.isoformat() + "Z"
    }
    
    print("🔍 Testando análise de carteira nova...")
    print(f"📅 Carteira criada há: 12 horas")
    print(f"💰 Valor da transação: $5,000")
    print(f"⚠️  Deve disparar alerta: new_wallet_interaction (threshold: 24h)\n")
    
    try:
        # Fazer requisição para API
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze/transaction",
            json=transaction_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Resposta da API:")
            print(f"🚨 Suspeita: {result['analysis_result']['is_suspicious']}")
            print(f"📊 Risk Score: {result['analysis_result']['risk_score']}")
            print(f"⚡ Regras disparadas: {result['analysis_result']['triggered_rules']}")
            
            # Verificar se new_wallet_interaction foi detectada
            if "new_wallet_interaction" in result['analysis_result']['triggered_rules']:
                print("✅ SUCCESS: Regra new_wallet_interaction detectada!")
                
                # Mostrar detalhes do alerta
                for alert in result['alerts']:
                    if alert['rule_name'] == 'new_wallet_interaction':
                        print(f"📝 Título: {alert['title']}")
                        print(f"📄 Descrição: {alert['description']}")
                        break
            else:
                print("❌ FAIL: Regra new_wallet_interaction não foi detectada")
            
            # Verificar contexto
            if 'context' in result and 'used_fundeddate' in result['context']:
                print(f"📋 Usou fundeddate: {result['context']['used_fundeddate']}")
            
        else:
            print(f"❌ Erro na API: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API")
        print("💡 Certifique-se de que o servidor está rodando: python start.py")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def test_old_wallet_analysis():
    """Testa análise de carteira antiga (não deve disparar alerta)"""
    
    current_time = datetime.now()
    
    # Carteira criada há 72 horas (não deve disparar alerta)
    funded_time = current_time - timedelta(hours=72)
    
    transaction_data = {
        "hash": "0xabcdef1234567890abcdef1234567890abcdef12",
        "from_address": "0x742d35Cc631C0532925a3b8D33C9",
        "to_address": "0xF977814e90dA44bFA03b6295",
        "value": 5000.0,
        "gas_price": 25.0,
        "timestamp": current_time.isoformat() + "Z",
        "block_number": 23197705,
        "transaction_type": "TRANSFER",
        "fundeddate_from": funded_time.isoformat() + "Z"
    }
    
    print("\n🔍 Testando análise de carteira antiga...")
    print(f"📅 Carteira criada há: 72 horas")
    print(f"💰 Valor da transação: $5,000")
    print(f"✅ Não deve disparar alerta: new_wallet_interaction (threshold: 24h)\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze/transaction",
            json=transaction_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Resposta da API:")
            print(f"🚨 Suspeita: {result['analysis_result']['is_suspicious']}")
            print(f"⚡ Regras disparadas: {result['analysis_result']['triggered_rules']}")
            
            if "new_wallet_interaction" not in result['analysis_result']['triggered_rules']:
                print("✅ SUCCESS: Regra new_wallet_interaction não foi detectada (correto)")
            else:
                print("❌ FAIL: Regra new_wallet_interaction foi detectada incorretamente")
                
        else:
            print(f"❌ Erro na API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🧪 Teste da funcionalidade fundeddate_from/fundeddate_to\n")
    test_new_wallet_analysis()
    test_old_wallet_analysis()
    print("\n🏁 Teste concluído!")
