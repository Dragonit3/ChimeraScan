# 🛡️ ChimeraScan
## Sistema de Detecção de Fraudes em Blockchain Ethereum

Sistema enterprise de detecção de fraudes em tempo real para transações Ethereum, com dashboard interativo, alertas automáticos e ferramentas ## 📊 Dashboard Features

- **⏱️ Real-time**: Atualização a cada 3 segundos
- **📊 Gráficos**: Risk score e volume de transações
- **🚨 Alertas**: Lista interativa com detalhes
- **📱 Responsivo**: Funciona em mobile e desktop
- **🔍 Modal**: Popup com informações detalhadas da transação
- **🆕 Persistência**: Alertas mantidos após reinicialização
- **🆕 Limpar Histórico**: Reset completo com confirmaçãoise manual.

## ⚡ Quick Start

### 1. Instalação
```bash
git clone <repo>
cd ChimeraScan-Challange
pip install -r requirements.txt
```

### 2. Executar Sistema Completo
```bash
# Inicia API + Dashboard
python start.py
```
**Dashboard**: http://localhost:5000

### 3. Iniciar Monitoramento
```bash
# Em terminal separado - Modo demonstração
python continuous_monitor.py

# OU Modo blockchain real (requer API keys)
python continuous_monitor.py --mode real
```

## 🎯 Funcionalidades Principais

### ✅ Dashboard em Tempo Real
- **Métricas**: Uptime, transações analisadas, alertas gerados
- **Gráficos**: Risk score e volume em tempo real com Plotly.js
- **Alertas**: Lista interativa com popup detalhado
- **Múltiplos Alertas**: Suporte a vários alertas por transação
- **🆕 Persistência**: Alertas mantidos após reinicialização
- **🆕 Limpar Histórico**: Botão para reset completo do sistema
- **🆕 Relatórios PDF**: Geração automática de relatórios profissionais

### ✅ Sistema de Detecção
- **Carteiras Novas**: Detecta carteiras criadas recentemente (`fundeddate`)
- **Alto Valor**: Transações acima de $10,000 USD
- **Blacklist Database**: Sistema completo de blacklist com SQLite
- **Risk Score**: Pontuação 0.0-1.0 baseada em múltiplos fatores
- **🆕 Persistência**: Banco de dados SQLite unificado (`chimera_data.db`)
- **🆕 Context Data**: Informações detalhadas preservadas em JSON

### ✅ Banco de Dados de Blacklist
- **SQLite**: Banco persistente para endereços suspeitos
- **Gerenciador Interativo**: Menu completo para administração
- **Múltiplos Tipos**: WALLET, CONTRACT, EXCHANGE, MIXER
- **Severidade**: LOW, MEDIUM, HIGH, CRITICAL com fallback automático

### ✅ Blockchain Real
- **Etherscan API**: Dados reais de funding de carteiras
- **Infura**: Monitoramento de blocos Ethereum em tempo real
- **Fallback**: Retorna para simulação se APIs falharem

### ✅ Ferramenta de Análise Manual
```bash
# Analisador interativo (passo-a-passo)
python manual_transaction_analyzer.py
```

## 📋 API Endpoints

### Análise de Transação
```bash
POST /api/v1/analyze/transaction
Content-Type: application/json

{
  "transaction_hash": "0x123...",
  "from_address": "0xabc...",
  "to_address": "0xdef...",
  "value_usd": 15000,
  "gas_price_gwei": 35.2,
  "fundeddate_from": "2025-08-24T23:10:00Z",
  "fundeddate_to": "2025-08-24T20:00:00Z"
}
```

### Consultar Alertas
```bash
GET /api/v1/alerts
GET /api/v1/alerts/stats
GET /api/v1/metrics/realtime
GET /health

# 🆕 Limpar histórico completo
POST /api/v1/database/clear-alerts

# 🆕 Gerar relatório PDF
POST /api/v1/reports/generate-pdf
GET /api/v1/reports/download/<filename>
```

## 🔧 Configuração

### Modo Real (Blockchain)
```bash
# 1. Copiar arquivo de configuração
cp .env.example .env

# 2. Configurar APIs (gratuitas)
# Infura: https://infura.io/
INFURA_URL=https://mainnet.infura.io/v3/SEU_PROJECT_ID

# Etherscan: https://etherscan.io/apis
ETHERSCAN_API_KEY=SUA_API_KEY

# Blacklist Database: https://etherscan.io/apis
DATABASE_BLACKLIST_URL=sqlite:///blacklist.db

# 3. Executar com dados reais
python continuous_monitor.py --mode real
```

### Gerenciar Blacklist
```bash
# Gerenciador interativo de blacklist
python manage_blacklist.py

# Opções disponíveis:
# 1. Criar novo banco de blacklist
# 2. Conectar a banco existente
# 3. Listar endereços na blacklist
# 4. Buscar endereço específico
# 5. Adicionar endereço à blacklist
# 6. Remover endereço da blacklist
# 7. Ver estatísticas
# 8. Inicializar dados de exemplo
```

### Personalizar Regras
Edite `config/rules.json`:
```json
{
  "high_value_threshold_usd": 10000,
  "new_wallet_threshold_hours": 24,
  "blacklisted_addresses": [
    "0x1234567890abcdef1234567890abcdef12345678"
  ]
}
```

## 📊 Exemplos de Uso

### Análise Manual - Interativa
```bash
python manual_transaction_analyzer.py

# Interface guiada:
# Hash: 0xtest123
# From: 0x1234567890abcdef1234567890abcdef12345678
# To: 0x9876543210fedcba9876543210fedcba98765432
# Valor: 15000
# Gas: 35.2
```

### Análise Manual - Linha de Comando
```bash
# Transação com alto valor
python quick_analyzer.py 0xtest123 \
  0x1234567890abcdef1234567890abcdef12345678 \
  15000 \
  --to 0x9876543210fedcba9876543210fedcba98765432 \
  --gas 35.2

# Resultado:
# 📊 RESULTADO:
#    Suspeita: ✅ NÃO
#    Risk Score: 0.341
#    Alertas: 3
# 🚨 ALERTAS DETECTADOS:
#    🟠 High Value Transfer: $15,000.00 (HIGH)
#    🟡 New Wallet Interaction: 3.4h old (MEDIUM)
#    🔴 Blacklisted Address Interaction (CRITICAL)
```

## 📁 Estrutura do Projeto

```
ChimeraScan/
├── core/                    # Lógica de detecção
│   ├── fraud_detector.py    # Engine principal
│   ├── rule_engine.py       # Regras customizáveis
│   └── risk_scorer.py       # Pontuação de risco
├── blockchain/              # Integração blockchain
│   └── ethereum_monitor.py  # Monitor Ethereum
├── alerts/                  # Sistema de alertas
│   └── alert_manager.py     # Gerenciador de alertas
├── dashboard/               # Interface web
│   ├── static/             
│   │   ├── dashboard.js     # Frontend JavaScript
│   │   └── styles.css       # Estilos CSS
│   └── templates/
│       └── index.html       # Dashboard HTML
├── config/                  # Configurações
│   ├── rules.json          # Regras de detecção
│   └── settings.py         # Configurações gerais
├── data/                    # Modelos de dados
│   └── models.py           # SQLAlchemy models
├── start.py                 # Inicialização
├── continuous_monitor.py    # Monitor contínuo
├── manual_transaction_analyzer.py  # Análise manual interativa
```

## 🔍 Tipos de Alertas

| Severidade | Tipo | Descrição | Threshold |
|------------|------|-----------|-----------|
| 🟠 **HIGH** | High Value Transfer | Transações de alto valor | ≥ $10,000 |
| 🟡 **MEDIUM** | New Wallet Interaction | Carteiras criadas recentemente | ≤ 24h |
| 🔴 **CRITICAL** | Blacklisted Address | Endereços na blacklist | Imediato |

## 🛠️ Tecnologias

- **Backend**: Python 3.12, Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript, Plotly.js
- **Blockchain**: Web3.py, Etherscan API, Infura
- **Database**: SQLite
- **Logs**: Estruturados com timestamps

## 📈 Dashboard Features

- **⏱️ Real-time**: Atualização a cada 3 segundos
- **📊 Gráficos**: Risk score e volume de transações
- **🚨 Alertas**: Lista interativa com detalhes
- **📱 Responsivo**: Funciona em mobile e desktop
- **🔍 Modal**: Popup com informações detalhadas da transação
- **🆕 Persistência**: Alertas mantidos após reinicialização
- **🆕 Limpar Histórico**: Reset completo com confirmação
- **🆕 Relatórios PDF**: Geração de relatórios profissionais com um clique

## 🚨 Troubleshooting

### Problemas Comuns

**Porta 5000 ocupada**
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Modo real não funciona**
```bash
# Verificar configuração
python -c "import os; print('INFURA_URL:', os.getenv('INFURA_URL', 'NÃO CONFIGURADO'))"

# Testar manualmente
python quick_analyzer.py 0xtest 0x1234567890abcdef1234567890abcdef12345678 1000
```

**Dashboard não atualiza**
- Verificar se `continuous_monitor.py` está rodando
- Checar console do browser (F12) para erros JavaScript
- Testar endpoint: http://localhost:5000/api/v1/metrics/realtime

**Banco de dados corrompido**
```bash
# Backup do banco atual
copy chimera_data.db chimera_data.db.backup

# Limpar via dashboard ou API
curl -X POST http://localhost:5000/api/v1/database/clear-alerts
```

## 📝 Documentação Adicional
- **API**: `API_DOCUMENTATION.md`
- **🆕 Database Integration**: `DATABASE_INTEGRATION.md`
- **🆕 Blacklist System**: `BLACKLIST_DATABASE.md`

---

**Desenvolvido para TecBan Challenge 2025**
