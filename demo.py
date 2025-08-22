"""
Script de demonstração do Sistema de Detecção de Fraudes TecBan
Simula transações suspeitas para demonstrar as funcionalidades
"""
import requests
import json
import time
from datetime import datetime, timedelta
import random

# URL base da API
BASE_URL = "http://localhost:5000"

def create_sample_transactions():
    """Cria transações de exemplo para demonstração"""
    
    # Transação normal
    normal_tx = {
        "hash": "0x1234567890abcdef1234567890abcdef12345678901234567890abcdef12345678",
        "from_address": "0x742d35cc6671c3f5c32cf8e0f4f85b1e4f8c8c1a",
        "to_address": "0x8ba1f109551bd432803012645hac136c0d8f8e56",
        "value": 1000.0,  # $1k - valor normal
        "gas_price": 25.0,  # Gas normal
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "block_number": 18500000,
        "transaction_type": "TRANSFER"
    }
    
    # Transação suspeita - Alto valor
    high_value_tx = {
        "hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "from_address": "0x123456789abcdef123456789abcdef123456789a",
        "to_address": "0x987654321fedcba987654321fedcba987654321b",
        "value": 750000.0,  # $750k - ALTO VALOR
        "gas_price": 30.0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "block_number": 18500001,
        "transaction_type": "TRANSFER"
    }
    
    # Transação suspeita - Horário + Gas alto
    suspicious_tx = {
        "hash": "0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
        "from_address": "0xsuspicious1234567890abcdef1234567890abcdef",
        "to_address": "0xnewwallet1234567890abcdef1234567890abcdef",
        "value": 50000.0,  # $50k
        "gas_price": 150.0,  # GAS MUITO ALTO
        "timestamp": (datetime.utcnow().replace(hour=2, minute=30)).isoformat() + "Z",  # 2:30 AM
        "block_number": 18500002,
        "transaction_type": "TRANSFER"
    }
    
    # Transação crítica - Múltiplos fatores
    critical_tx = {
        "hash": "0xcritical1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "from_address": "0x1234567890abcdef1234567890abcdef12345678",  # Endereço na blacklist simulada
        "to_address": "0xexchange1234567890abcdef1234567890abcdef",
        "value": 999999.0,  # Quase 1M - valor redondo suspeito
        "gas_price": 200.0,  # Gas extremamente alto
        "timestamp": (datetime.utcnow().replace(hour=3, minute=0)).isoformat() + "Z",  # 3:00 AM - horário suspeito
        "block_number": 18500003,
        "transaction_type": "TRANSFER"
    }
    
    return [normal_tx, high_value_tx, suspicious_tx, critical_tx]

def analyze_transaction(transaction):
    """Analisa uma transação usando a API"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze/transaction",
            json=transaction,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erro na análise: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API. Certifique-se de que o sistema está rodando.")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None

def print_analysis_result(transaction, result):
    """Imprime resultado da análise de forma formatada"""
    if not result:
        return
    
    analysis = result["analysis_result"]
    
    print(f"\n{'='*60}")
    print(f"📊 ANÁLISE DE TRANSAÇÃO")
    print(f"{'='*60}")
    print(f"🔗 Hash: {transaction['hash'][:20]}...")
    print(f"💰 Valor: ${transaction['value']:,.2f}")
    print(f"⛽ Gas Price: {transaction['gas_price']} Gwei")
    print(f"📅 Timestamp: {transaction['timestamp']}")
    
    # Status de risco
    risk_emoji = {
        "LOW": "🟢",
        "MEDIUM": "🟡", 
        "HIGH": "🟠",
        "CRITICAL": "🔴"
    }
    
    print(f"\n🎯 RESULTADO DA ANÁLISE:")
    print(f"   Suspeito: {'❌ SIM' if analysis['is_suspicious'] else '✅ NÃO'}")
    print(f"   Risk Score: {analysis['risk_score']:.3f}")
    print(f"   Nível de Risco: {risk_emoji.get(analysis['risk_level'], '⚪')} {analysis['risk_level']}")
    print(f"   Regras Ativadas: {len(analysis['triggered_rules'])}")
    print(f"   Alertas Gerados: {analysis['alert_count']}")
    
    # Regras ativadas
    if analysis['triggered_rules']:
        print(f"\n⚠️  REGRAS ATIVADAS:")
        for rule in analysis['triggered_rules']:
            print(f"   • {rule.replace('_', ' ').title()}")
    
    # Alertas
    if result.get('alerts'):
        print(f"\n🚨 ALERTAS GERADOS:")
        for alert in result['alerts']:
            severity_emoji = {
                "LOW": "🟢",
                "MEDIUM": "🟡",
                "HIGH": "🟠", 
                "CRITICAL": "🔴"
            }
            print(f"   {severity_emoji.get(alert['severity'], '⚪')} [{alert['severity']}] {alert['title']}")
            print(f"      {alert['description']}")
    
    # Contexto
    if result.get('context'):
        context = result['context']
        print(f"\n📋 CONTEXTO ADICIONAL:")
        print(f"   • Tempo de Análise: {context.get('analysis_duration_ms', 0):.1f}ms")
        print(f"   • Regras Avaliadas: {context.get('rules_evaluated', 0)}")
        if 'wallet_age_hours' in context:
            print(f"   • Idade da Carteira: {context['wallet_age_hours']:.1f}h")
        if 'gas_price_ratio' in context:
            print(f"   • Razão Gas Price: {context['gas_price_ratio']:.1f}x")

def check_system_status():
    """Verifica se o sistema está funcionando"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            if health["status"] == "healthy":
                print("✅ Sistema online e funcionando")
                return True
            else:
                print(f"⚠️  Sistema em estado: {health['status']}")
                return False
        else:
            print(f"❌ Sistema retornou status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao sistema")
        return False

def get_system_stats():
    """Obtém estatísticas do sistema"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/stats")
        if response.status_code == 200:
            stats = response.json()
            
            print(f"\n📊 ESTATÍSTICAS DO SISTEMA:")
            print(f"{'='*40}")
            
            detection_stats = stats.get("detection_stats", {})
            print(f"🔍 Transações Analisadas: {detection_stats.get('total_analyzed', 0)}")
            print(f"⚠️  Suspeitas Detectadas: {detection_stats.get('suspicious_detected', 0)}")
            print(f"🚨 Alertas Gerados: {detection_stats.get('alerts_generated', 0)}")
            
            if detection_stats.get('total_analyzed', 0) > 0:
                rate = (detection_stats.get('suspicious_detected', 0) / detection_stats.get('total_analyzed', 1)) * 100
                print(f"📈 Taxa de Detecção: {rate:.1f}%")
            
            system_info = stats.get("system_info", {})
            print(f"⏱️  Uptime: {system_info.get('uptime_hours', 0):.1f}h")
            print(f"🔧 Versão: {system_info.get('version', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")

def main():
    """Função principal da demonstração"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           🛡️  ChimeraScan Demo                 ║
    ║                                                          ║
    ║         Demonstração do Sistema de Detecção              ║
    ║              de Fraudes em Blockchain                    ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Verificar status do sistema
    print("🔍 Verificando status do sistema...")
    if not check_system_status():
        print("\n💡 Para iniciar o sistema, execute:")
        print("   python start.py")
        return
    
    # Obter estatísticas iniciais
    get_system_stats()
    
    # Criar transações de exemplo
    print(f"\n🧪 Iniciando demonstração com transações de exemplo...")
    transactions = create_sample_transactions()
    
    transaction_types = [
        "Normal (Baixo Risco)",
        "Alto Valor (Alto Risco)", 
        "Suspeita (Gas Alto + Horário)",
        "Crítica (Múltiplos Fatores)"
    ]
    
    # Analisar cada transação
    for i, (transaction, tx_type) in enumerate(zip(transactions, transaction_types)):
        print(f"\n🔄 Analisando transação {i+1}/4: {tx_type}")
        time.sleep(1)  # Pausa dramática
        
        result = analyze_transaction(transaction)
        if result:
            print_analysis_result(transaction, result)
        
        # Pausa entre análises
        #if i < len(transactions) - 1:
            #input("\n⏸️  Pressione Enter para continuar...")
    
    # Estatísticas finais
    print(f"\n🏁 Demonstração concluída!")
    get_system_stats()
    
    print(f"\n💡 Acesse o dashboard em: {BASE_URL}")
    print("📊 Visualize os alertas e métricas em tempo real!")

if __name__ == "__main__":
    main()
