# 🚫 ChimeraScan - Banco de Dados de Blacklist

Sistema de blacklist baseado em SQLite para detecção de endereços suspeitos em tempo real.

## 📋 Configuração Inicial

### 1. Variável de Ambiente
Adicione no arquivo `.env`:
```bash
DATABASE_BLACKLIST_URL=sqlite:///blacklist.db
```

### 2. Estrutura do Banco de Dados

#### Tabela: `blacklisted_addresses`
```sql
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
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_address_lookup ON blacklisted_addresses(address, is_active);
CREATE INDEX IF NOT EXISTS idx_severity ON blacklisted_addresses(severity_level);
CREATE INDEX IF NOT EXISTS idx_created_at ON blacklisted_addresses(created_at);
```

#### Campos da Tabela

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | INTEGER | ID único do registro | 1 |
| `address` | TEXT | Endereço Ethereum (obrigatório) | 0x1234...abcd |
| `address_type` | TEXT | Tipo do endereço | WALLET, CONTRACT, EXCHANGE |
| `severity_level` | TEXT | Nível de severidade | LOW, MEDIUM, HIGH, CRITICAL |
| `reason` | TEXT | Motivo da inclusão | "Phishing", "Ransomware" |
| `source` | TEXT | Fonte da informação | "FBI", "Chainalysis", "Manual" |
| `created_at` | TIMESTAMP | Data de criação | 2025-08-30 10:30:00 |
| `updated_at` | TIMESTAMP | Data da última atualização | 2025-08-30 10:30:00 |
| `is_active` | BOOLEAN | Se está ativo | TRUE/FALSE |
| `notes` | TEXT | Observações adicionais | "Confirmado em múltiplas fontes" |

## 🔧 Comandos SQL para Configuração

### Criar Banco e Tabela
```sql
-- 1. Criar a tabela principal
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
);

-- 2. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_address_lookup ON blacklisted_addresses(address, is_active);
CREATE INDEX IF NOT EXISTS idx_severity ON blacklisted_addresses(severity_level);
CREATE INDEX IF NOT EXISTS idx_created_at ON blacklisted_addresses(created_at);

-- 3. Trigger para atualizar updated_at automaticamente
CREATE TRIGGER IF NOT EXISTS update_blacklist_timestamp 
    AFTER UPDATE ON blacklisted_addresses
BEGIN
    UPDATE blacklisted_addresses 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;
```

## 📝 Exemplos de Uso

### Adicionar Endereços na Blacklist

#### 1. Endereços de Phishing
```sql
INSERT INTO blacklisted_addresses (address, address_type, severity_level, reason, source, notes) VALUES
('0x1234567890abcdef1234567890abcdef12345678', 'WALLET', 'CRITICAL', 'Phishing wallet confirmed', 'Chainalysis', 'Multiple victims reported'),
('0xabcdef1234567890abcdef1234567890abcdef12', 'WALLET', 'HIGH', 'Suspected phishing', 'Community Report', 'Similar pattern to known phisher'),
('0xd4648f90A20f5bbBFFEEb0d6E7C62C9396174F2b', 'CONTRACT', 'CRITICAL', 'Malicious smart contract', 'Security Audit', 'Honeypot contract');
```

#### 2. Endereços de Ransomware
```sql
INSERT INTO blacklisted_addresses (address, address_type, severity_level, reason, source, notes) VALUES
('0xdAFC4ab80F48FdE24591aA4412a9d924EaDc0a58', 'WALLET', 'CRITICAL', 'Ransomware payment address', 'FBI Report', 'WannaCry variant'),
('0x42C529af2f7c1FE094501a9986E6723733154b82', 'WALLET', 'CRITICAL', 'Ransomware operator', 'Europol', 'Multiple campaigns'),
('0xcfAf9660251648a3723f21172e2A4D1257b2b372', 'WALLET', 'HIGH', 'Suspected ransomware', 'Behavioral Analysis', 'Large inflows from multiple sources');
```

#### 3. Exchanges Suspeitas
```sql
INSERT INTO blacklisted_addresses (address, address_type, severity_level, reason, source, notes) VALUES
('0x7751C71663A22CF8375eA1d259640bbc46db63a7', 'EXCHANGE', 'MEDIUM', 'Unregulated exchange', 'Regulatory Authority', 'No KYC compliance'),
('0xDe87b67Cc523270F896Fa9C7c3B21e287101567d', 'EXCHANGE', 'HIGH', 'Mixer service', 'FATF Guidelines', 'Used for money laundering');
```

#### 4. Endereços de Teste (para desenvolvimento)
```sql
INSERT INTO blacklisted_addresses (address, address_type, severity_level, reason, source, notes) VALUES
('0x00d9fE085D99B33Ab2AAE8063180c63E23bF2E69', 'WALLET', 'MEDIUM', 'Test address for ChimeraScan', 'Internal', 'Used for testing blacklist functionality'),
('0x455bF23eA7575A537b6374953FA71B5F3653272c', 'WALLET', 'LOW', 'Demo suspicious address', 'Internal', 'Demo purposes only');
```

### Consultar Blacklist

#### Verificar Endereço Específico
```sql
SELECT * FROM blacklisted_addresses 
WHERE address = '0x1234567890abcdef1234567890abcdef12345678' 
AND is_active = TRUE;
```

#### Listar por Severidade
```sql
SELECT address, reason, severity_level, created_at 
FROM blacklisted_addresses 
WHERE severity_level = 'CRITICAL' 
AND is_active = TRUE 
ORDER BY created_at DESC;
```

#### Estatísticas da Blacklist
```sql
SELECT 
    severity_level,
    COUNT(*) as total,
    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active
FROM blacklisted_addresses 
GROUP BY severity_level;
```

### Gerenciar Blacklist

#### Desativar Endereço (ao invés de deletar)
```sql
UPDATE blacklisted_addresses 
SET is_active = FALSE, 
    updated_at = CURRENT_TIMESTAMP,
    notes = notes || ' [DEACTIVATED: False positive]'
WHERE address = '0x1234567890abcdef1234567890abcdef12345678';
```

#### Atualizar Severidade
```sql
UPDATE blacklisted_addresses 
SET severity_level = 'CRITICAL',
    reason = 'Confirmed ransomware operator',
    updated_at = CURRENT_TIMESTAMP
WHERE address = '0xabcdef1234567890abcdef1234567890abcdef12';
```

## 🔍 Script de Inicialização

Crie um arquivo `init_blacklist.sql` com dados iniciais:

```sql
-- ChimeraScan Blacklist Initialization Script
-- Execute este script para configurar a blacklist inicial

-- Criar tabela e índices
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
);

CREATE INDEX IF NOT EXISTS idx_address_lookup ON blacklisted_addresses(address, is_active);
CREATE INDEX IF NOT EXISTS idx_severity ON blacklisted_addresses(severity_level);
CREATE INDEX IF NOT EXISTS idx_created_at ON blacklisted_addresses(created_at);

-- Inserir dados iniciais (endereços conhecidamente suspeitos)
INSERT OR IGNORE INTO blacklisted_addresses (address, address_type, severity_level, reason, source, notes) VALUES
-- Phishing Wallets
('0x1234567890abcdef1234567890abcdef12345678', 'WALLET', 'CRITICAL', 'Known phishing wallet', 'Chainalysis', 'Multiple confirmed victims'),
('0xabcdef1234567890abcdef1234567890abcdef12', 'WALLET', 'HIGH', 'Suspected phishing', 'Community Report', 'Pattern analysis match'),

-- Ransomware Addresses  
('0xd4648f90A20f5bbBFFEEb0d6E7C62C9396174F2b', 'WALLET', 'CRITICAL', 'Ransomware payment address', 'FBI Cyber Division', 'Multiple ransomware campaigns'),
('0xdAFC4ab80F48FdE24591aA4412a9d924EaDc0a58', 'WALLET', 'CRITICAL', 'Ransomware operator', 'Europol', 'Confirmed criminal activity'),

-- Mixer/Tumbler Services
('0x42C529af2f7c1FE094501a9986E6723733154b82', 'CONTRACT', 'HIGH', 'Unauthorized mixer service', 'FATF Guidelines', 'AML compliance violation'),
('0xcfAf9660251648a3723f21172e2A4D1257b2b372', 'CONTRACT', 'MEDIUM', 'Privacy service', 'Regulatory Watch', 'Under investigation'),

-- Suspicious Exchanges
('0x7751C71663A22CF8375eA1d259640bbc46db63a7', 'EXCHANGE', 'HIGH', 'Unregulated exchange', 'Financial Authority', 'No proper licensing'),
('0xDe87b67Cc523270F896Fa9C7c3B21e287101567d', 'EXCHANGE', 'MEDIUM', 'High-risk exchange', 'Risk Assessment', 'Unusual transaction patterns'),

-- Test/Demo Addresses
('0x00d9fE085D99B33Ab2AAE8063180c63E23bF2E69', 'WALLET', 'LOW', 'ChimeraScan test address', 'Internal', 'Used for system testing'),
('0x455bF23eA7575A537b6374953FA71B5F3653272c', 'WALLET', 'MEDIUM', 'Demo suspicious wallet', 'Internal', 'Demonstration purposes');

-- Verificar inserção
SELECT COUNT(*) as total_addresses FROM blacklisted_addresses WHERE is_active = TRUE;
```

## 🚀 Comandos de Linha

### Usando sqlite3 CLI
```bash
# Conectar ao banco
sqlite3 blacklist.db

# Executar script de inicialização
.read init_blacklist.sql

# Verificar dados
SELECT address, severity_level, reason FROM blacklisted_addresses LIMIT 5;

# Sair
.quit
```

### Usando Python
```python
import sqlite3
import os

# Conectar usando a variável de ambiente
db_url = os.getenv('DATABASE_BLACKLIST_URL', 'sqlite:///blacklist.db')
db_path = db_url.replace('sqlite:///', '')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar endereço
address = "0x1234567890abcdef1234567890abcdef12345678"
cursor.execute("""
    SELECT address, severity_level, reason 
    FROM blacklisted_addresses 
    WHERE address = ? AND is_active = TRUE
""", (address.lower(),))

result = cursor.fetchone()
if result:
    print(f"⚠️  Endereço blacklistado: {result[0]} - {result[1]} - {result[2]}")
else:
    print("✅ Endereço não encontrado na blacklist")

conn.close()
```

## 📊 Monitoramento e Manutenção

### Consultas Úteis para Administração

```sql
-- Estatísticas gerais
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active,
    COUNT(CASE WHEN severity_level = 'CRITICAL' THEN 1 END) as critical
FROM blacklisted_addresses;

-- Endereços adicionados recentemente
SELECT address, reason, severity_level, created_at 
FROM blacklisted_addresses 
WHERE created_at >= datetime('now', '-7 days')
ORDER BY created_at DESC;

-- Limpar endereços de teste antigos
DELETE FROM blacklisted_addresses 
WHERE source = 'Internal' 
AND reason LIKE '%test%' 
AND created_at < datetime('now', '-30 days');
```

## 🔒 Segurança e Backup

### Backup do Banco
```bash
# Backup completo
sqlite3 blacklist.db ".backup backup_$(date +%Y%m%d).db"

# Export para SQL
sqlite3 blacklist.db ".dump" > blacklist_backup.sql

# Restore do backup
sqlite3 new_blacklist.db ".restore backup_20250830.db"
```

### Permissões Recomendadas
```bash
# Definir permissões apropriadas (Linux/Mac)
chmod 640 blacklist.db
chown app:app blacklist.db
```

---

**⚠️ Importante**: Sempre validar endereços antes de adicionar à blacklist. Endereços incorretos podem causar falsos positivos e impactar operações legítimas.
