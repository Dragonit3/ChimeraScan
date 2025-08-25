#!/usr/bin/env python3
"""
Analisador Manual de Transações - ChimeraScan
Permite inserir dados de transação manualmente e analisar via API
"""
import requests
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import sys

class ManualTransactionAnalyzer:
    """Classe para análise manual de transações via API"""
    
    def __init__(self, api_base_url="http://localhost:5000"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def check_api_health(self) -> bool:
        """Verifica se a API está rodando"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API está online - Status: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ API retornou status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Não foi possível conectar à API em {self.api_base_url}")
            print("   Certifique-se de que a API está rodando: python start.py")
            return False
        except Exception as e:
            print(f"❌ Erro ao verificar API: {e}")
            return False
    
    def get_transaction_input(self) -> Dict[str, Any]:
        """Coleta dados da transação via input do usuário"""
        print("\n" + "="*60)
        print("🔍 ANÁLISE MANUAL DE TRANSAÇÃO - CHIMERASCAN")
        print("="*60)
        
        transaction_data = {}
        
        # Hash da transação
        while True:
            tx_hash = input("\n📝 Hash da transação (ex: 0x123abc...): ").strip()
            if tx_hash:
                transaction_data["hash"] = tx_hash
                break
            print("❌ Hash da transação é obrigatório!")
        
        # Endereços das carteiras
        while True:
            from_address = input("📤 From Address (carteira origem): ").strip()
            if from_address:
                transaction_data["from_address"] = from_address
                break
            print("❌ From Address é obrigatório!")
        
        to_address = input("📥 To Address (carteira destino - opcional): ").strip()
        if to_address:
            transaction_data["to_address"] = to_address
        
        # Valor da transação
        while True:
            try:
                value = input("💰 Valor da transação (em USD): $").strip()
                transaction_data["value"] = float(value)
                break
            except ValueError:
                print("❌ Valor deve ser um número válido!")
        
        # Gas price
        while True:
            try:
                gas_price = input("⛽ Gas Price (em Gwei, ex: 25.5): ").strip()
                transaction_data["gas_price"] = float(gas_price)
                break
            except ValueError:
                print("❌ Gas Price deve ser um número válido!")
        
        # Timestamp da transação
        print("\n⏰ Timestamp da transação:")
        print("1. Usar timestamp atual")
        print("2. Inserir data/hora personalizada")
        
        choice = input("Escolha (1 ou 2): ").strip()
        if choice == "2":
            while True:
                try:
                    date_str = input("📅 Data/hora (formato: YYYY-MM-DD HH:MM:SS): ").strip()
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    dt = dt.replace(tzinfo=timezone.utc)
                    transaction_data["timestamp"] = dt.isoformat()
                    break
                except ValueError:
                    print("❌ Formato inválido! Use: YYYY-MM-DD HH:MM:SS")
        else:
            transaction_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Block number
        while True:
            try:
                block_number = input("🧱 Block Number (ex: 23199150): ").strip()
                transaction_data["block_number"] = int(block_number)
                break
            except ValueError:
                print("❌ Block Number deve ser um número inteiro!")
        
        # Fundeddate das carteiras
        print("\n" + "-"*40)
        print("📊 DATAS DE FUNDING DAS CARTEIRAS")
        print("-"*40)
        
        # Fundeddate From
        print(f"\n🏦 Data de funding da carteira FROM ({from_address[:10]}...):")
        print("1. Não informar (carteira antiga)")
        print("2. Inserir data de funding")
        
        choice = input("Escolha (1 ou 2): ").strip()
        if choice == "2":
            while True:
                try:
                    date_str = input("📅 Data/hora funding FROM (YYYY-MM-DD HH:MM:SS): ").strip()
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    dt = dt.replace(tzinfo=timezone.utc)
                    transaction_data["fundeddate_from"] = dt.isoformat()
                    break
                except ValueError:
                    print("❌ Formato inválido! Use: YYYY-MM-DD HH:MM:SS")
        
        # Fundeddate To (se existe to_address)
        if to_address:
            print(f"\n🏦 Data de funding da carteira TO ({to_address[:10]}...):")
            print("1. Não informar (carteira antiga)")
            print("2. Inserir data de funding")
            
            choice = input("Escolha (1 ou 2): ").strip()
            if choice == "2":
                while True:
                    try:
                        date_str = input("📅 Data/hora funding TO (YYYY-MM-DD HH:MM:SS): ").strip()
                        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        dt = dt.replace(tzinfo=timezone.utc)
                        transaction_data["fundeddate_to"] = dt.isoformat()
                        break
                    except ValueError:
                        print("❌ Formato inválido! Use: YYYY-MM-DD HH:MM:SS")
        
        return transaction_data
    
    def analyze_transaction(self, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Envia transação para análise via API"""
        try:
            print("\n" + "="*60)
            print("🔄 ENVIANDO PARA ANÁLISE...")
            print("="*60)
            
            # Mostrar dados que serão enviados
            print("\n📋 Dados da transação:")
            for key, value in transaction_data.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f"   {key}: {value[:47]}...")
                else:
                    print(f"   {key}: {value}")
            
            # Enviar para API
            response = self.session.post(
                f"{self.api_base_url}/api/v1/analyze/transaction",
                json=transaction_data
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
                
        except Exception as e:
            print(f"❌ Erro ao analisar transação: {e}")
            return None
    
    def display_results(self, result: Dict[str, Any]) -> None:
        """Exibe os resultados da análise"""
        print("\n" + "="*60)
        print("📊 RESULTADOS DA ANÁLISE")
        print("="*60)
        
        # Informações gerais
        analysis = result.get("analysis_result", {})
        print(f"\n🎯 Resultado Geral:")
        print(f"   Suspeita: {'🚨 SIM' if analysis.get('is_suspicious', False) else '✅ NÃO'}")
        print(f"   Risk Score: {analysis.get('risk_score', 0):.4f}")
        print(f"   Risk Level: {analysis.get('risk_level', 'UNKNOWN')}")
        print(f"   Regras Ativadas: {len(analysis.get('triggered_rules', []))}")
        
        # Alertas gerados
        alerts = result.get("alerts", [])
        print(f"\n🚨 Alertas Gerados: {len(alerts)}")
        
        if alerts:
            for i, alert in enumerate(alerts, 1):
                severity = alert.get("severity", "UNKNOWN")
                severity_icon = {
                    "LOW": "🟢",
                    "MEDIUM": "🟡", 
                    "HIGH": "🟠",
                    "CRITICAL": "🔴"
                }.get(severity, "⚪")
                
                print(f"\n   {severity_icon} Alerta {i}: {alert.get('title', 'Sem título')}")
                print(f"      Severidade: {severity}")
                print(f"      Regra: {alert.get('rule_name', 'Desconhecida')}")
                print(f"      Descrição: {alert.get('description', 'Sem descrição')}")
                print(f"      Risk Score: {alert.get('risk_score', 0):.4f}")
        else:
            print("   ✅ Nenhum alerta gerado - transação parece limpa")
        
        # Contexto adicional
        context = result.get("context", {})
        if context:
            print(f"\n📋 Informações Adicionais:")
            print(f"   Duração da Análise: {context.get('analysis_duration_ms', 0):.1f}ms")
            print(f"   Regras Avaliadas: {context.get('rules_evaluated', 0)}")
            print(f"   Tipo de Transação: {context.get('transaction_type', 'UNKNOWN')}")
            if context.get('wallet_age_hours'):
                print(f"   Idade da Carteira: {context.get('wallet_age_hours', 0):.1f} horas")
        
        print(f"\n⏰ Análise realizada em: {result.get('analyzed_at', 'Desconhecido')}")
        print("\n" + "="*60)
    
    def run_interactive_mode(self):
        """Executa o modo interativo"""
        print("🛡️  ChimeraScan - Analisador Manual de Transações")
        print("Versão 1.0.0 - TecBan Challenge")
        
        # Verificar se API está online
        if not self.check_api_health():
            print("\n❌ Não é possível continuar sem conexão com a API")
            return
        
        while True:
            try:
                # Coletar dados da transação
                transaction_data = self.get_transaction_input()
                
                # Analisar transação
                result = self.analyze_transaction(transaction_data)
                
                if result:
                    # Exibir resultados
                    self.display_results(result)
                else:
                    print("❌ Falha na análise da transação")
                
                # Perguntar se quer analisar outra transação
                print("\n" + "="*60)
                choice = input("🔄 Analisar outra transação? (s/n): ").strip().lower()
                if choice not in ['s', 'sim', 'y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Saindo do analisador...")
                break
            except Exception as e:
                print(f"\n❌ Erro inesperado: {e}")
                choice = input("🔄 Tentar novamente? (s/n): ").strip().lower()
                if choice not in ['s', 'sim', 'y', 'yes']:
                    break

def main():
    """Função principal"""
    analyzer = ManualTransactionAnalyzer()
    analyzer.run_interactive_mode()

if __name__ == "__main__":
    main()
