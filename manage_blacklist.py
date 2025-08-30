#!/usr/bin/env python3
"""
ChimeraScan - Gerenciador de Blacklist
Script interativo para gerenciar banco de dados de blacklist
"""
import sqlite3
import os
from datetime import datetime
from enum import Enum
from typing import List, Tuple, Optional

class SeverityLevel(Enum):
    """Níveis de severidade para blacklist"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AddressType(Enum):
    """Tipos de endereço"""
    WALLET = "WALLET"
    CONTRACT = "CONTRACT"
    EXCHANGE = "EXCHANGE"
    MIXER = "MIXER"
    OTHER = "OTHER"

class BlacklistManager:
    """Gerenciador de blacklist com funcionalidades completas"""
    
    def __init__(self, db_path: str = None):
        """Inicializa o gerenciador"""
        self.db_path = db_path
        self.connected = False
    
    def connect_database(self, db_path: str) -> bool:
        """Conecta ao banco de dados"""
        try:
            self.db_path = db_path
            # Testar conexão
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
            self.connected = True
            print(f"✅ Conectado ao banco: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            self.connected = False
            return False
    
    def create_database(self, db_path: str) -> bool:
        """Cria um novo banco de dados de blacklist"""
        try:
            print(f"📁 Criando banco de dados: {db_path}")
            
            with sqlite3.connect(db_path) as conn:
                # Criar tabela principal
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS blacklisted_addresses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        address TEXT NOT NULL UNIQUE,
                        address_type TEXT NOT NULL,
                        severity_level TEXT NOT NULL DEFAULT 'HIGH',
                        reason TEXT,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        notes TEXT
                    )
                """)
                
                # Criar índices para performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_address_lookup ON blacklisted_addresses(address, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_severity ON blacklisted_addresses(severity_level)",
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON blacklisted_addresses(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_address_type ON blacklisted_addresses(address_type)"
                ]
                
                for index_sql in indexes:
                    conn.execute(index_sql)
                
                # Criar trigger para atualizar timestamp
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_blacklist_timestamp 
                        AFTER UPDATE ON blacklisted_addresses
                    BEGIN
                        UPDATE blacklisted_addresses 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE id = NEW.id;
                    END
                """)
                
                conn.commit()
                print("✅ Estrutura do banco criada com sucesso")
                
                # Conectar ao novo banco
                self.connect_database(db_path)
                return True
                
        except Exception as e:
            print(f"❌ Erro ao criar banco: {e}")
            return False
    
    def list_addresses(self, limit: int = 20, filter_severity: str = None) -> bool:
        """Lista endereços na blacklist"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Construir query
                base_query = """
                    SELECT id, address, address_type, severity_level, reason, source, created_at, is_active
                    FROM blacklisted_addresses
                """
                params = []
                
                if filter_severity:
                    base_query += " WHERE severity_level = ? AND is_active = TRUE"
                    params.append(filter_severity.upper())
                else:
                    base_query += " WHERE is_active = TRUE"
                
                base_query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(base_query, params)
                results = cursor.fetchall()
                
                if not results:
                    print("📭 Nenhum endereço encontrado na blacklist")
                    return True
                
                print(f"\n📋 ENDEREÇOS NA BLACKLIST ({len(results)} resultados)")
                print("=" * 80)
                
                for row in results:
                    id_val, address, addr_type, severity, reason, source, created_at, is_active = row
                    status = "🟢 ATIVO" if is_active else "🔴 INATIVO"
                    
                    severity_emoji = {
                        "CRITICAL": "🔴",
                        "HIGH": "🟠", 
                        "MEDIUM": "🟡",
                        "LOW": "🟢"
                    }.get(severity, "⚪")
                    
                    print(f"\n🆔 ID: {id_val} | {status}")
                    print(f"📍 Endereço: {address}")
                    print(f"🏷️  Tipo: {addr_type}")
                    print(f"{severity_emoji} Severidade: {severity}")
                    print(f"📄 Motivo: {reason or 'N/A'}")
                    print(f"📋 Fonte: {source or 'N/A'}")
                    print(f"📅 Criado em: {created_at}")
                    print("-" * 80)
                
                return True
                
        except Exception as e:
            print(f"❌ Erro ao listar endereços: {e}")
            return False
    
    def add_address(self, address: str, address_type: str, severity_level: str, 
                   reason: str = None, source: str = None, notes: str = None) -> bool:
        """Adiciona um endereço à blacklist"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        # Validar endereço Ethereum
        if not address.startswith('0x') or len(address) != 42:
            print("❌ Endereço Ethereum inválido. Deve começar com 0x e ter 42 caracteres")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verificar se já existe
                cursor = conn.execute("""
                    SELECT id, is_active FROM blacklisted_addresses 
                    WHERE LOWER(address) = LOWER(?)
                """, (address,))
                
                existing = cursor.fetchone()
                if existing:
                    if existing[1]:  # is_active
                        print(f"⚠️  Endereço {address} já está na blacklist (ID: {existing[0]})")
                        return False
                    else:
                        # Reativar endereço inativo
                        conn.execute("""
                            UPDATE blacklisted_addresses 
                            SET is_active = TRUE, 
                                address_type = ?,
                                severity_level = ?,
                                reason = ?,
                                source = ?,
                                notes = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (address_type, severity_level, reason, source, notes, existing[0]))
                        conn.commit()
                        print(f"✅ Endereço {address} reativado na blacklist")
                        return True
                
                # Inserir novo endereço
                conn.execute("""
                    INSERT INTO blacklisted_addresses 
                    (address, address_type, severity_level, reason, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (address, address_type, severity_level, reason, source, notes))
                
                conn.commit()
                print(f"✅ Endereço {address} adicionado à blacklist com severidade {severity_level}")
                return True
                
        except Exception as e:
            print(f"❌ Erro ao adicionar endereço: {e}")
            return False
    
    def remove_address(self, identifier: str, permanent: bool = False) -> bool:
        """Remove um endereço da blacklist"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Determinar se é ID ou endereço
                if identifier.isdigit():
                    # É um ID
                    field = "id"
                    value = int(identifier)
                elif identifier.startswith('0x'):
                    # É um endereço
                    field = "LOWER(address)"
                    value = identifier.lower()
                else:
                    print("❌ Identificador inválido. Use ID numérico ou endereço 0x...")
                    return False
                
                # Verificar se existe
                if field == "id":
                    cursor = conn.execute("SELECT address, is_active FROM blacklisted_addresses WHERE id = ?", (value,))
                else:
                    cursor = conn.execute("SELECT address, is_active FROM blacklisted_addresses WHERE LOWER(address) = ?", (value,))
                
                existing = cursor.fetchone()
                if not existing:
                    print(f"❌ Endereço não encontrado: {identifier}")
                    return False
                
                address, is_active = existing
                if not is_active and not permanent:
                    print(f"⚠️  Endereço {address} já está inativo")
                    return False
                
                if permanent:
                    # Deletar permanentemente
                    if field == "id":
                        conn.execute("DELETE FROM blacklisted_addresses WHERE id = ?", (value,))
                    else:
                        conn.execute("DELETE FROM blacklisted_addresses WHERE LOWER(address) = ?", (value,))
                    print(f"🗑️  Endereço {address} removido permanentemente")
                else:
                    # Soft delete (marcar como inativo)
                    if field == "id":
                        conn.execute("""
                            UPDATE blacklisted_addresses 
                            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (value,))
                    else:
                        conn.execute("""
                            UPDATE blacklisted_addresses 
                            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE LOWER(address) = ?
                        """, (value,))
                    print(f"🔒 Endereço {address} desativado (soft delete)")
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Erro ao remover endereço: {e}")
            return False
    
    def search_address(self, search_term: str) -> bool:
        """Busca um endereço específico"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, address, address_type, severity_level, reason, source, created_at, updated_at, is_active, notes
                    FROM blacklisted_addresses 
                    WHERE LOWER(address) LIKE LOWER(?) OR reason LIKE ? OR source LIKE ?
                    ORDER BY created_at DESC
                """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
                
                results = cursor.fetchall()
                
                if not results:
                    print(f"📭 Nenhum resultado encontrado para: {search_term}")
                    return True
                
                print(f"\n🔍 RESULTADOS DA BUSCA: '{search_term}' ({len(results)} encontrados)")
                print("=" * 80)
                
                for row in results:
                    id_val, address, addr_type, severity, reason, source, created_at, updated_at, is_active, notes = row
                    status = "🟢 ATIVO" if is_active else "🔴 INATIVO"
                    
                    severity_emoji = {
                        "CRITICAL": "🔴",
                        "HIGH": "🟠",
                        "MEDIUM": "🟡", 
                        "LOW": "🟢"
                    }.get(severity, "⚪")
                    
                    print(f"\n🆔 ID: {id_val} | {status}")
                    print(f"📍 Endereço: {address}")
                    print(f"🏷️  Tipo: {addr_type}")
                    print(f"{severity_emoji} Severidade: {severity}")
                    print(f"📄 Motivo: {reason or 'N/A'}")
                    print(f"📋 Fonte: {source or 'N/A'}")
                    print(f"📅 Criado: {created_at}")
                    print(f"🔄 Atualizado: {updated_at}")
                    if notes:
                        print(f"📝 Notas: {notes}")
                    print("-" * 80)
                
                return True
                
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return False
    
    def get_statistics(self) -> bool:
        """Mostra estatísticas da blacklist"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Estatísticas gerais
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active,
                        COUNT(CASE WHEN is_active = 0 THEN 1 END) as inactive
                    FROM blacklisted_addresses
                """)
                total, active, inactive = cursor.fetchone()
                
                # Por severidade
                cursor = conn.execute("""
                    SELECT severity_level, COUNT(*) as count
                    FROM blacklisted_addresses 
                    WHERE is_active = 1
                    GROUP BY severity_level
                """)
                severity_stats = dict(cursor.fetchall())
                
                # Por tipo
                cursor = conn.execute("""
                    SELECT address_type, COUNT(*) as count
                    FROM blacklisted_addresses 
                    WHERE is_active = 1
                    GROUP BY address_type
                """)
                type_stats = dict(cursor.fetchall())
                
                # Atividade recente
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM blacklisted_addresses 
                    WHERE created_at >= datetime('now', '-7 days')
                """)
                recent = cursor.fetchone()[0]
                
                print(f"\n📊 ESTATÍSTICAS DA BLACKLIST")
                print("=" * 40)
                print(f"📁 Banco: {self.db_path}")
                print(f"📊 Total de entradas: {total}")
                print(f"🟢 Entradas ativas: {active}")
                print(f"🔴 Entradas inativas: {inactive}")
                print(f"📅 Adicionadas nos últimos 7 dias: {recent}")
                
                print(f"\n🚨 POR SEVERIDADE (apenas ativas):")
                for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    count = severity_stats.get(severity, 0)
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
                    print(f"   {emoji} {severity}: {count}")
                
                print(f"\n🏷️  POR TIPO (apenas ativas):")
                for addr_type in ["WALLET", "CONTRACT", "EXCHANGE", "MIXER", "OTHER"]:
                    count = type_stats.get(addr_type, 0)
                    print(f"   📍 {addr_type}: {count}")
                
                return True
                
        except Exception as e:
            print(f"❌ Erro ao obter estatísticas: {e}")
            return False
    
    def initialize_sample_data(self) -> bool:
        """Inicializa dados de exemplo"""
        if not self.connected:
            print("❌ Não conectado ao banco de dados")
            return False
        
        sample_data = [
            # Phishing Wallets
            ("0x1234567890abcdef1234567890abcdef12345678", "WALLET", "CRITICAL", 
             "Known phishing wallet", "Chainalysis", "Multiple confirmed victims"),
            ("0xabcdef1234567890abcdef1234567890abcdef12", "WALLET", "HIGH", 
             "Suspected phishing", "Community Report", "Pattern analysis match"),
            
            # Ransomware Addresses
            ("0xd4648f90A20f5bbBFFEEb0d6E7C62C9396174F2b", "WALLET", "CRITICAL", 
             "Ransomware payment address", "FBI Cyber Division", "Multiple ransomware campaigns"),
            ("0xdAFC4ab80F48FdE24591aA4412a9d924EaDc0a58", "WALLET", "CRITICAL", 
             "Ransomware operator", "Europol", "Confirmed criminal activity"),
            
            # Mixer Services
            ("0x42C529af2f7c1FE094501a9986E6723733154b82", "CONTRACT", "HIGH", 
             "Unauthorized mixer service", "FATF Guidelines", "AML compliance violation"),
            ("0xcfAf9660251648a3723f21172e2A4D1257b2b372", "CONTRACT", "MEDIUM", 
             "Privacy service", "Regulatory Watch", "Under investigation"),
            
            # Test Addresses
            ("0x00d9fE085D99B33Ab2AAE8063180c63E23bF2E69", "WALLET", "LOW", 
             "ChimeraScan test address", "Internal", "Used for system testing"),
            ("0x455bF23eA7575A537b6374953FA71B5F3653272c", "WALLET", "MEDIUM", 
             "Demo suspicious wallet", "Internal", "Demonstration purposes")
        ]
        
        success_count = 0
        for data in sample_data:
            if self.add_address(*data):
                success_count += 1
        
        print(f"✅ Inicializados {success_count}/{len(sample_data)} endereços de exemplo")
        return success_count > 0


def show_menu():
    """Mostra o menu principal"""
    print("\n" + "=" * 60)
    print("🛡️  CHIMERASCAN - GERENCIADOR DE BLACKLIST")
    print("=" * 60)
    print("1. 🗃️  Criar novo banco de blacklist")
    print("2. 🔗 Conectar a banco existente") 
    print("3. 📋 Listar endereços na blacklist")
    print("4. 🔍 Buscar endereço específico")
    print("5. ➕ Adicionar endereço à blacklist")
    print("6. ❌ Remover endereço da blacklist")
    print("7. 📊 Ver estatísticas")
    print("8. 🚀 Inicializar dados de exemplo")
    print("9. 🚪 Sair")
    print("=" * 60)

def get_user_input(prompt: str, required: bool = True) -> str:
    """Obtém entrada do usuário com validação"""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("❌ Este campo é obrigatório")

def get_choice(options: dict, prompt: str) -> str:
    """Obtém escolha do usuário de um dicionário de opções"""
    print(f"\n{prompt}")
    for key, value in options.items():
        print(f"{key}. {value}")
    
    while True:
        choice = input("Escolha: ").strip()
        if choice in options:
            return options[choice]
        print("❌ Escolha inválida")

def main():
    """Função principal"""
    manager = BlacklistManager()
    
    print("🛡️  ChimeraScan - Gerenciador de Blacklist")
    print("Versão 2.0.0 - Interface Completa")
    
    while True:
        show_menu()
        choice = input("Escolha uma opção (1-9): ").strip()
        
        if choice == '1':
            # Criar novo banco
            print("\n📁 CRIAR NOVO BANCO DE BLACKLIST")
            print("-" * 40)
            db_name = get_user_input("Nome do arquivo do banco (ex: blocklist.db): ")
            if not db_name.endswith('.db'):
                db_name += '.db'
            
            if os.path.exists(db_name):
                overwrite = input(f"⚠️  Arquivo {db_name} já existe. Sobrescrever? (s/n): ").strip().lower()
                if overwrite != 's':
                    continue
            
            if manager.create_database(db_name):
                print("✅ Banco criado e conectado com sucesso!")
        
        elif choice == '2':
            # Conectar a banco existente
            print("\n🔗 CONECTAR A BANCO EXISTENTE")
            print("-" * 40)
            db_path = get_user_input("Caminho do banco de dados: ")
            if not os.path.exists(db_path):
                print(f"❌ Arquivo não encontrado: {db_path}")
                continue
            manager.connect_database(db_path)
        
        elif choice == '3':
            # Listar endereços
            print("\n📋 LISTAR ENDEREÇOS")
            print("-" * 40)
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            
            limit = input("Limite de resultados (padrão 20): ").strip()
            limit = int(limit) if limit.isdigit() else 20
            
            filter_options = {
                '1': None,
                '2': 'CRITICAL',
                '3': 'HIGH', 
                '4': 'MEDIUM',
                '5': 'LOW'
            }
            print("\nFiltrar por severidade:")
            print("1. Todos")
            print("2. CRITICAL")
            print("3. HIGH")
            print("4. MEDIUM") 
            print("5. LOW")
            
            filter_choice = input("Escolha (1-5): ").strip()
            severity_filter = filter_options.get(filter_choice)
            
            manager.list_addresses(limit, severity_filter)
        
        elif choice == '4':
            # Buscar endereço
            print("\n🔍 BUSCAR ENDEREÇO")
            print("-" * 40)
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            
            search_term = get_user_input("Termo de busca (endereço, motivo ou fonte): ")
            manager.search_address(search_term)
        
        elif choice == '5':
            # Adicionar endereço
            print("\n➕ ADICIONAR ENDEREÇO")
            print("-" * 40)
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            
            address = get_user_input("Endereço Ethereum (0x...): ")
            
            type_options = {
                '1': 'WALLET',
                '2': 'CONTRACT',
                '3': 'EXCHANGE',
                '4': 'MIXER',
                '5': 'OTHER'
            }
            addr_type = get_choice(type_options, "Tipo de endereço:")
            
            severity_options = {
                '1': 'LOW',
                '2': 'MEDIUM', 
                '3': 'HIGH',
                '4': 'CRITICAL'
            }
            severity = get_choice(severity_options, "Nível de severidade:")
            
            reason = get_user_input("Motivo da inclusão: ", required=False)
            source = get_user_input("Fonte da informação: ", required=False)
            notes = get_user_input("Observações adicionais: ", required=False)
            
            manager.add_address(address, addr_type, severity, reason, source, notes)
        
        elif choice == '6':
            # Remover endereço
            print("\n❌ REMOVER ENDEREÇO")
            print("-" * 40)
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            
            identifier = get_user_input("ID numérico ou endereço (0x...): ")
            
            permanent = input("Remoção permanente? (s/n, padrão: n): ").strip().lower() == 's'
            
            manager.remove_address(identifier, permanent)
        
        elif choice == '7':
            # Estatísticas
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            manager.get_statistics()
        
        elif choice == '8':
            # Inicializar dados de exemplo
            print("\n🚀 INICIALIZAR DADOS DE EXEMPLO")
            print("-" * 40)
            if not manager.connected:
                print("❌ Conecte-se primeiro a um banco de dados")
                continue
            
            confirm = input("Isso adicionará endereços de exemplo. Continuar? (s/n): ").strip().lower()
            if confirm == 's':
                manager.initialize_sample_data()
        
        elif choice == '9':
            # Sair
            print("👋 Saindo do gerenciador...")
            break
        
        else:
            print("❌ Opção inválida")
        
        # Pausa para o usuário ver o resultado
        input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    main()
