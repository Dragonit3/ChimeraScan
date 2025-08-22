# ChimeraScan System
## Sistema de Detecção de Fraudes em Ativos Tokenizados

### 🎯 Objetivo
Detectar e mitigar fraudes em transações de ativos tokenizados na blockchain Ethereum, com foco em aplicações institucionais. Sistema completo com dashboard em tempo real, alertas automáticos e API REST para integração.

### 🏗️ Arquitetura
- **Separation of Concerns**: Módulos independentes para monitoramento, detecção, alertas
- **Real-time Dashboard**: Interface web com atualizações em tempo real
- **Escalabilidade**: Arquitetura preparada para alto volume de transações
- **Manutenibilidade**: Código modular e documentado
- **Adaptabilidade**: Regras customizáveis por instituição
- **Performance**: Cache, processamento assíncrono e otimizações

### 📁 Estrutura do Projeto
```
fraud-detection-system/
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── fraud_detector.py    # Motor principal de detecção
│   ├── rule_engine.py       # Engine de regras customizáveis
│   └── risk_scorer.py       # Sistema de pontuação de risco
├── blockchain/              # Integração blockchain
│   ├── __init__.py
│   └── ethereum_monitor.py  # Monitor de transações Ethereum
├── detection/               # Algoritmos de detecção (pasta vazia - expansão futura)
├── alerts/                  # Sistema de alertas
│   ├── __init__.py
│   └── alert_manager.py     # Gerenciamento de alertas
├── data/                    # Camada de dados
│   ├── __init__.py
│   └── models.py            # Modelos de dados (TransactionData, AlertData)
├── dashboard/               # Dashboard web
│   ├── static/
│   │   ├── dashboard.js     # JavaScript do dashboard
│   │   └── styles.css       # Estilos CSS
│   └── templates/
│       └── index.html       # Template principal
├── config/                  # Configurações
│   ├── __init__.py
│   ├── settings.py          # Configurações gerais
│   └── rules.json           # Regras de detecção
├── main.py                  # Aplicação Flask principal
├── continuous_monitor.py    # Monitor contínuo de transações
├── demo.py                  # Demonstração do sistema
├── start.py                 # Script de inicialização
├── run_complete_system.py   # Executor do sistema completo
├── test_api.py             # Testes da API
├── .env.example            # Exemplo de variáveis de ambiente
└── requirements.txt        # Dependências
```

### 🚀 Funcionalidades Implementadas
1. **Dashboard em Tempo Real**: 
   - Métricas de sistema (uptime, transações analisadas, alertas)
   - Gráficos de risk score e volume de transações em tempo real
   - Lista de alertas recentes com scroll automático
   - Distribuição de alertas por severidade

2. **Monitoramento Contínuo**: 
   - **Modo Simulação**: Geração de transações realísticas para demonstração
   - **Modo Real**: Integração com blockchain Ethereum via Infura/Alchemy
   - Processamento de blocos reais em tempo real
   - Análise de transações da mainnet Ethereum
   - Suporte a APIs Etherscan para informações detalhadas

3. **Sistema de Alertas**: 
   - Classificação automática por severidade (LOW, MEDIUM, HIGH, CRITICAL)
   - Armazenamento persistente de alertas
   - API REST para consulta de alertas

4. **API REST Completa**:
   - `/health` - Status do sistema
   - `/api/v1/metrics/realtime` - Métricas em tempo real
   - `/api/v1/alerts` - Lista de alertas
   - `/api/v1/stats` - Estatísticas gerais

5. **Engine de Detecção**:
   - Análise de risco baseada em múltiplos fatores
   - Regras customizáveis via JSON
   - Pontuação de risco de 0.0 a 1.0

### 🔧 Tecnologias Utilizadas
- **Backend**: Python 3.8+, Flask 2.x, SQLAlchemy
- **Database**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Plotly.js
- **Blockchain**: Web3.py, simulação de dados Ethereum
- **Logs**: Structlog para logging estruturado
- **Cache**: Redis (configurado, não utilizado no demo)

### 🚀 Como Executar

#### Pré-requisitos
```bash
pip install -r requirements.txt
```

#### Componentes Separados
```bash
# Terminal 1: Servidor principal
python start.py

# Terminal Opção 1: Monitor de transações (modo simulação)
python continuous_monitor.py

# Terminal Opção 2: Monitor com dados reais da blockchain
python continuous_monitor.py --mode real

# Terminal Opção 3: Demonstração de dados
python demo.py
```

#### Opção 3: Modo Real com Blockchain
```bash
# Configurar variáveis de ambiente primeiro
cp .env.example .env
# Editar .env com suas chaves de API
```

#### Acesso ao Dashboard
- **URL**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **API Docs**: Consultar endpoints na seção de funcionalidades

### 📊 Endpoints da API

#### Métricas em Tempo Real
```
GET /api/v1/metrics/realtime
```
Retorna métricas atualizadas do sistema incluindo uptime, transações analisadas, alertas gerados e scores de risco.

#### Alertas do Sistema  
```
GET /api/v1/alerts
```
Lista todos os alertas com paginação, filtros por severidade e ordenação por timestamp.

#### Status do Sistema
```
GET /health
```
Verifica se todos os componentes estão funcionando corretamente.

### 🔧 Configuração

#### Variáveis de Ambiente
Copie `.env.example` para `.env` e configure:
```bash
cp .env.example .env
```

**Para Modo Real de Blockchain:**
```bash
# Obtenha chave gratuita em https://infura.io/
INFURA_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID

# Obtenha chave gratuita em https://etherscan.io/apis  
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
```

#### Personalização de Regras
Edite `config/rules.json` para customizar regras de detecção por instituição.

### � Integração com Blockchain Real

#### Modos de Operação

**🎭 Modo Simulação (Padrão)**
- Gera transações realísticas para demonstração
- Ideal para desenvolvimento e testes
- Não requer chaves de API externas

**🌐 Modo Real**  
- Conecta com a blockchain Ethereum mainnet
- Processa transações reais em tempo real
- Requer chaves de API (Infura + Etherscan)

#### Configuração para Modo Real

1. **Obter Chave Infura (Gratuita)**:
   - Visite https://infura.io/
   - Crie conta e projeto
   - Copie o Project ID

2. **Obter Chave Etherscan (Gratuita)**:
   - Visite https://etherscan.io/apis
   - Crie conta
   - Gere API key gratuita

3. **Configurar .env**:
   ```bash
   INFURA_URL=https://mainnet.infura.io/v3/SEU_PROJECT_ID
   ETHERSCAN_API_KEY=SUA_API_KEY
   ```

4. **Executar Modo Real**:
   ```bash
   python continuous_monitor.py --mode real
   ```

#### Características do Modo Real

- **Latência**: ~12-15 segundos entre blocos (tempo natural do Ethereum)
- **Volume**: Processa até 5 transações por bloco
- **Limitação**: 3 blocos por ciclo para evitar rate limits
- **Fallback**: Retorna automaticamente ao modo simulação se APIs falharem
- **Logs Detalhados**: Mostra valores em ETH e Gwei reais

### �🏗️ Arquitetura do Sistema

O sistema segue uma arquitetura modular com separação clara de responsabilidades:

- **Core**: Lógica principal de detecção de fraudes
- **Blockchain**: Integração e monitoramento de blockchain  
- **Alerts**: Gerenciamento e classificação de alertas
- **Data**: Modelos de dados e persistência
- **Dashboard**: Interface web responsiva
- **Config**: Configurações centralizadas

### 📈 Características Técnicas

- **Real-time Updates**: Dashboard atualiza a cada 3 segundos
- **Fixed Time Windows**: Gráficos mantêm janelas de tempo consistentes
- **Responsive Design**: Interface adaptável a diferentes tamanhos de tela
- **Error Handling**: Tratamento robusto de erros e logging
- **Modular Architecture**: Facilita manutenção e expansão
- **SQLite Integration**: Persistência local para desenvolvimento
- **Async Processing**: Processamento assíncrono de transações

### 🐛 Troubleshooting

#### Problemas Comuns

**Erro: "Port 5000 already in use"**
```bash
# Encontrar processo usando a porta
netstat -ano | findstr :5000
# Matar processo se necessário
taskkill /PID <PID> /F
```

**Dashboard não atualiza**
- Verifique se `continuous_monitor.py` está rodando
- Confirme que a API `/api/v1/metrics/realtime` retorna dados
- Verifique console do browser para erros JavaScript

**Banco de dados não encontrado**
- O sistema cria automaticamente `fraud_detection.db`
- Verifique permissões de escrita na pasta do projeto

**Alertas não aparecem**
- Execute `python demo.py` para gerar dados de teste
- Verifique logs do sistema para erros

**Modo Real não funciona**
- Verifique se INFURA_URL está configurado no arquivo .env
- Confirme que a chave da API está válida
- Sistema fará fallback automático para modo simulação se houver problemas
- Use `python continuous_monitor.py --mode real` para forçar modo real

**Transações reais muito lentas**
- Blocos Ethereum são gerados a cada ~12-15 segundos
- Use `--interval 10` para intervalos maiores em modo real
- Sistema processa até 3 blocos por ciclo para evitar sobrecarga

### 📝 Desenvolvimento

#### Estrutura de Commits
- `feat:` Nova funcionalidade
- `fix:` Correção de bug  
- `docs:` Documentação
- `refactor:` Refatoração de código
- `test:` Testes

#### Expansões Futuras
- [x] **Integração com APIs reais de blockchain** ✅ **IMPLEMENTADO**
  - Suporte a Infura/Alchemy para dados reais da Ethereum
  - Integração com Etherscan API
  - Monitoramento de blocos em tempo real
  - Fallback automático para modo simulação
- [ ] Machine Learning para detecção de anomalias
- [ ] Notificações por email/webhook
- [ ] Autenticação e autorização
- [ ] Deploy em containers Docker
- [ ] Monitoramento com Prometheus/Grafana

### 📄 Licença
Este projeto foi desenvolvido como demonstração técnica para o TecBan Challenge.
