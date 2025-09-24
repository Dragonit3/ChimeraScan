// ChimeraScan Dashboard JavaScript

class FraudDashboard {
    constructor() {
        this.isConnected = false;
        this.updateInterval = 5000; // 5 segundos
        this.charts = {};
        this.utcOffset = null; // Will be loaded from backend
        this.timezoneConfig = null; // Full timezone configuration
        this.updateTimer = null; // Timer para atualizações em tempo real
        this.init();
    }

    async init() {
        console.log('Initializing ChimeraScan Dashboard...');
        
        // Step 1: Check API connectivity
        await this.checkConnection();
        
        // Step 2: Load timezone configuration FIRST (critical for all date/time display)
        await this.loadTimezoneConfig();
        console.log(`Dashboard configured for timezone: ${this.timezoneConfig?.timezone_name || 'UTC'}`);
        
        // Step 3: Initialize UI components (now with proper timezone config)
        this.initializeCharts();
        this.bindEventListeners();
        
        // Step 4: Load initial data (will use proper timezone formatting)
        await this.loadDashboardData();
        
        // Step 5: Start real-time updates ONLY ONCE
        this.startRealTimeUpdates();

        console.log('Dashboard initialized successfully');
    }

    // Debug method to display current timezone configuration
    getTimezoneDebugInfo() {
        return {
            utcOffset: this.utcOffset,
            timezoneConfig: this.timezoneConfig,
            currentTime: new Date().toISOString(),
            formattedCurrentTime: this.formatFullDateTime(new Date().toISOString())
        };
    }

    async loadTimezoneConfig() {
        try {
            console.log('Loading timezone configuration from backend...');
            const response = await fetch('/api/v1/config/timezone');
            if (response.ok) {
                this.timezoneConfig = await response.json();
                this.utcOffset = this.timezoneConfig.utc_offset;
                console.log('Timezone configuration loaded:', this.timezoneConfig);
                console.log('UTC Offset set to:', this.utcOffset);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Failed to load timezone configuration:', error);
            console.error('This indicates a configuration or network issue.');
            // Emergency fallback to UTC - should not happen in production
            this.utcOffset = 0;
            this.timezoneConfig = {
                utc_offset: 0,
                timezone_name: "UTC",
                description: "Emergency fallback to UTC due to configuration error"
            };
        }
    }

    async checkConnection() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.isConnected = true;
                this.updateConnectionStatus(true);
            } else {
                throw new Error('API not healthy');
            }
        } catch (error) {
            console.error('Connection check failed:', error);
            this.isConnected = false;
            this.updateConnectionStatus(false);
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (statusDot && statusText) {
            if (connected) {
                statusDot.style.backgroundColor = '#10b910ff'; // green
                statusText.textContent = 'Sistema Online';
            } else {
                statusDot.style.backgroundColor = '#ef4444'; // red
                statusText.textContent = 'Sistema Offline';
            }
        }
    }

    async loadDashboardData() {
        try {
            // Carregar estatísticas
            await this.loadStats();
            
            // Carregar alertas recentes
            await this.loadRecentAlerts();
            
            // Carregar regras ativas
            await this.loadActiveRules();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Erro ao carregar dados do dashboard');
        }
    }

    async loadStats() {
        try {
            // Usar endpoint de métricas em tempo real
            const response = await fetch('/api/v1/metrics/realtime');
            const data = await response.json();
            
            this.updateStatsCards(data);
            this.updateChartsData(data);
            
        } catch (error) {
            console.error('Error loading stats:', error);
            // Se falhar, usar dados zerados
            this.updateStatsCards({});
        }
    }

    updateStatsCards(data) {
        // Usar dados reais da API de métricas em tempo real
        
        // Total de transações analisadas
        this.updateMetricCard('total-analyzed', data.transactions_analyzed || 0);
        
        // Transações suspeitas
        this.updateMetricCard('suspicious-detected', data.suspicious_detected || 0);
        
        // Alertas gerados
        this.updateMetricCard('alerts-generated', data.total_alerts || 0);
        
        // Taxa de suspeitos (API já retorna em %)
        const detectionRate = data.detection_rate ? data.detection_rate.toFixed(1) : '0.0';
        this.updateMetricCard('suspicious-rate', detectionRate + '%');
        
        // Tempo online (converter segundos para horas)
        const uptimeHours = data.uptime_seconds ? (data.uptime_seconds / 3600).toFixed(1) : '0.0';
        this.updateMetricCard('uptime-hours', uptimeHours + 'h');
    }

    updateMetricCard(cardId, value, change = null) {
        const card = document.getElementById(cardId);
        if (card) {
            const valueElement = card.querySelector('.metric-value');
            if (valueElement) {
                valueElement.textContent = value;
                
                // Adicionar animação de atualização
                valueElement.classList.add('updated');
                setTimeout(() => valueElement.classList.remove('updated'), 1000);
            }
            
        }
    }

    async loadRecentAlerts() {
        try {
            // Usar endpoint real de alertas
            const response = await fetch('/api/v1/alerts');
            
            if (response.status === 200) {
                const data = await response.json();
                this.renderAlerts(data.alerts || []);
                // Atualizar gráfico de distribuição por severidade
                this.updateAlertsChart(data.alerts || []);
            } else {
                // Se não houver alertas ou erro, começar com lista vazia
                this.renderAlerts([]);
                this.updateAlertsChart([]);
            }
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            // Se falhar, começar com lista vazia
            this.renderAlerts([]);
            this.updateAlertsChart([]);
        }
    }

    renderAlerts(alerts) {
        const alertsContainer = document.getElementById('recent-alerts');
        if (!alertsContainer) return;

        if (alerts.length === 0) {
            alertsContainer.innerHTML = '<p class="text-center text-secondary">Nenhum alerta recente</p>';
            return;
        }

        // Mostrar TODOS os alertas sem limitação
        const recentAlerts = alerts;

        const alertsHtml = recentAlerts.map(alert => `
            <div class="alert-card card ${alert.severity.toLowerCase()}" 
                 data-alert-id="${alert.id}" 
                 onclick="dashboard.showAlertDetails('${alert.id}')">
                <div class="alert-title">${alert.title}</div>
                <div class="alert-description">${alert.description || 'undefined'}</div>
                <div class="alert-meta">
                    <span>Hash: <code>${alert.transaction_hash.substring(0, 10)}...</code></span>
                    <span class="risk-score">Score: ${alert.risk_score ? alert.risk_score.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="alert-meta mt-1">
                    <span>${this.formatTime(alert.detected_at || alert.created_at)}</span>
                    <span class="badge badge-${alert.severity.toLowerCase()}">${alert.severity}</span>
                </div>
                <div class="click-hint" style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.5rem;">
                    Clique para ver detalhes
                </div>
            </div>
        `).join('');

        alertsContainer.innerHTML = alertsHtml;
        
        // Armazenar dados dos alertas para uso no modal
        this.alertsData = alerts;
    }

    updateAlertsChart(alerts) {
        if (!this.charts.alerts || typeof Plotly === 'undefined') return;

        // Contar alertas por severidade
        const severityCounts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        };

        alerts.forEach(alert => {
            const severity = alert.severity.toUpperCase();
            if (severityCounts.hasOwnProperty(severity)) {
                severityCounts[severity]++;
            }
        });

        const data = [{
            x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            y: [severityCounts.CRITICAL, severityCounts.HIGH, severityCounts.MEDIUM, severityCounts.LOW],
            type: 'bar',
            marker: {
                color: ['#dc2626', '#ef4444', '#f59e0b', '#10b981']
            }
        }];

        const layout = {
            title: 'Distribuição de Alertas por Severidade',
            xaxis: { title: 'Severidade' },
            yaxis: { title: 'Quantidade' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f9fafb' },
            height: 430,
        };

        // Usar react em vez de redraw para maior confiabilidade
        Plotly.react(this.charts.alerts, data, layout, { responsive: true });
    }

    async loadActiveRules() {
        try {
            const response = await fetch('/api/v1/rules');
            const data = await response.json();
            
            // Usar regras configuradas para mostrar todas (ativas + pendentes)
            this.renderActiveRules(data.configured_rules || []);
            
        } catch (error) {
            console.error('Error loading rules:', error);
        }
    }

    renderActiveRules(rules) {
        const rulesContainer = document.getElementById('active-rules');
        if (!rulesContainer) return;

        if (rules.length === 0) {
            rulesContainer.innerHTML = '<p class="text-center text-secondary">Nenhuma regra ativa</p>';
            return;
        }

        const rulesHtml = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Regra</th>
                        <th>Severidade</th>
                        <th>Status</th>
                        <th>Ação</th>
                    </tr>
                </thead>
                <tbody>
                    ${rules.map(rule => `
                        <tr>
                            <td>
                                <strong>${rule.name.replace(/_/g, ' ').toUpperCase()}</strong>
                                <br>
                                <small class="text-secondary">${rule.description}</small>
                            </td>
                            <td><span class="badge badge-${rule.severity.toLowerCase()}">${rule.severity}</span></td>
                            <td>
                                <span class="badge ${this.getStatusBadgeClass(rule.status)}">
                                    ${rule.status === 'ACTIVE' ? 'ATIVA' : rule.status === 'CONFIGURED' ? 'CONFIGURADA' : 'INATIVA'}
                                </span>
                                ${rule.implemented ? 
                                    '<small class="text-success">✓ Implementada</small>' : 
                                    '<small class="text-warning">⚠ Pendente</small>'}
                            </td>
                            <td><small class="text-secondary">${rule.action}</small></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        rulesContainer.innerHTML = rulesHtml;
    }

    getStatusBadgeClass(status) {
        switch(status) {
            case 'ACTIVE': return 'badge-low';
            case 'CONFIGURED': return 'badge-medium';
            default: return 'badge-secondary';
        }
    }

    initializeCharts() {
        // Inicializar gráficos com Plotly.js (se disponível)
        if (typeof Plotly !== 'undefined') {
            this.initRiskScoreChart();
            this.initAlertsChart();
            this.initTransactionVolumeChart();
        }
    }

    initRiskScoreChart() {
        const chartElement = document.getElementById('risk-score-chart');
        if (!chartElement) return;

        // Gerar labels de tempo para os últimos 20 pontos (1 minuto)
        const timeLabels = this.generateRecentTimeLabels(20);
        
        // Iniciar com dados zerados
        const data = [{
            x: timeLabels,
            y: new Array(20).fill(0), // Começar zerado
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Risk Score',
            line: { color: '#F2C744' }, // Amarelo dourado
            marker: { size: 4, color: '#F2C744' }
        }];

        const layout = {
            title: 'Risk Score ao Longo do Tempo',
            autosize: true,
            xaxis: { 
                title: 'Tempo',
                fixedrange: true // Impedir zoom no eixo X
            },
            yaxis: { 
                title: 'Risk Score', 
                range: [0, 1],
                fixedrange: true // Impedir zoom no eixo Y
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f9fafb' },
            margin: { t: 50, r: 30, b: 80, l: 60 }
        };

        Plotly.newPlot(chartElement, data, layout, { 
            responsive: true,
            displayModeBar: false // Remover barra de ferramentas
        });
        this.charts.riskScore = chartElement;
    }

    initAlertsChart() {
        const chartElement = document.getElementById('alerts-chart');
        if (!chartElement) return;

        // Iniciar com dados zerados
        const data = [{
            x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            y: [0, 0, 0, 0], // Começar zerado
            type: 'bar',
            marker: {
                color: ['#dc2626', '#ef4444', '#f59e0b', '#10b981']
            }
        }];

        const layout = {
            title: 'Distribuição de Alertas por Severidade',
            xaxis: { title: 'Severidade' },
            yaxis: { title: 'Quantidade' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f9fafb' }
        };

        Plotly.newPlot(chartElement, data, layout, { responsive: true });
        this.charts.alerts = chartElement;
    }

    initTransactionVolumeChart() {
        const chartElement = document.getElementById('transaction-volume-chart');
        if (!chartElement) return;

        // Gerar labels de tempo para os últimos 15 pontos (45 segundos)
        const timeLabels = this.generateRecentTimeLabels(15);
        
        // Iniciar com dados zerados
        const data = [{
            x: timeLabels,
            y: new Array(15).fill(0), // Começar zerado
            type: 'scatter',
            mode: 'lines',
            fill: 'tonexty',
            fillcolor: 'rgba(242, 199, 68, 0.2)', // Amarelo dourado com transparência
            line: { color: '#F2C744' } // Amarelo dourado
        }];

        const layout = {
            title: 'Volume de Transações',
            xaxis: { 
                title: 'Tempo',
                fixedrange: true
            },
            yaxis: { 
                title: 'Transações',
                fixedrange: true
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f9fafb' },
            margin: { t: 50, r: 30, b: 80, l: 60 }
        };

        Plotly.newPlot(chartElement, data, layout, { 
            responsive: true,
            displayModeBar: false
        });
        this.charts.transactionVolume = chartElement;
    }

    updateChartsData(data) {
        // Atualizar gráfico de risk score com janela fixa de tempo
        if (this.charts.riskScore && typeof Plotly !== 'undefined' && data.average_risk_score !== undefined) {
            const currentTime = new Date();
            const timeLabel = currentTime.toLocaleTimeString('pt-BR', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
            
            // Obter dados atuais do gráfico
            const currentData = this.charts.riskScore.data[0];
            
            // Adicionar novo ponto
            const newX = [...currentData.x, timeLabel];
            const newY = [...currentData.y, data.average_risk_score];
            
            // Manter apenas os últimos 20 pontos (aproximadamente 1 minuto com updates a cada 3s)
            const maxPoints = 20;
            const finalX = newX.slice(-maxPoints);
            const finalY = newY.slice(-maxPoints);
            
            // Atualizar o gráfico com dados fixos
            Plotly.restyle(this.charts.riskScore, {
                x: [finalX],
                y: [finalY]
            }, [0]);
        }

        // Atualizar gráfico de volume de transações com janela fixa
        if (this.charts.transactionVolume && typeof Plotly !== 'undefined' && data.recent_volume !== undefined) {
            const currentTime = new Date();
            const timeLabel = currentTime.toLocaleTimeString('pt-BR', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
            
            // Obter dados atuais do gráfico
            const currentData = this.charts.transactionVolume.data[0];
            
            // Adicionar novo ponto (usando recent_volume ao invés de total)
            const newX = [...currentData.x, timeLabel];
            const newY = [...currentData.y, data.recent_volume];
            
            // Manter apenas os últimos 15 pontos (aproximadamente 45 segundos)
            const maxPoints = 15;
            const finalX = newX.slice(-maxPoints);
            const finalY = newY.slice(-maxPoints);
            
            // Atualizar o gráfico com dados fixos
            Plotly.restyle(this.charts.transactionVolume, {
                x: [finalX],
                y: [finalY]
            }, [0]);
        }
    }

    startRealTimeUpdates() {
        // Prevenir múltiplos timers
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        // Atualizar dados a cada intervalo configurado
        this.updateTimer = setInterval(async () => {
            if (this.isConnected) {
                await this.loadDashboardData();
            } else {
                await this.checkConnection();
            }
        }, this.updateInterval);
        
        console.log(`Real-time updates started with interval: ${this.updateInterval}ms`);
    }

    stopRealTimeUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
            console.log('Real-time updates stopped');
        }
    }

    destroy() {
        // Limpar recursos quando dashboard for destruído
        this.stopRealTimeUpdates();
    }

    bindEventListeners() {
        // Event listeners para interações do usuário
        document.addEventListener('click', (e) => {
            // Handler para cliques em alertas
            if (e.target.closest('.alert-card')) {
                const alertCard = e.target.closest('.alert-card');
                const alertId = alertCard.dataset.alertId;
                this.showAlertDetails(alertId);
            }
        });
    }

    showError(message) {
        // Mostrar mensagem de erro
        console.error(message);
        // Implementar sistema de notificações
    }

    // Funções utilitárias
    normalizeIsoToUtc(isoString) {
        // Garantir que a string ISO está em formato UTC correto
        if (!isoString) return null;
        
        // Se não termina com 'Z', adicionar (assumir UTC)
        if (!isoString.endsWith('Z') && !isoString.includes('+') && !isoString.includes('-', 10)) {
            return isoString + 'Z';
        }
        
        return isoString;
    }

    formatWithTimeZone(dateUtc, options) {
        // Aplicar offset de timezone configurado
        if (this.utcOffset === null || this.utcOffset === undefined) {
            // Fallback para UTC se timezone não carregado
            return dateUtc.toLocaleString('pt-BR', {
                ...options,
                timeZone: 'UTC'
            });
        }
        
        // Aplicar offset: Para UTC-3, somar -3 horas (subtrai 3h)
        const offsetDate = new Date(dateUtc.getTime() + (this.utcOffset * 60 * 60 * 1000));
        
        return offsetDate.toLocaleString('pt-BR', {
            ...options,
            timeZone: 'UTC' // Usar UTC pois já aplicamos o offset manualmente
        });
    }

    formatTime(isoString) {
        if (!isoString) return 'N/A';

        const norm = this.normalizeIsoToUtc(isoString);
        const dateUtc = new Date(norm);
        const nowUtc = new Date(); // epoch é sempre UTC

        const diffMs = nowUtc - dateUtc;
        const diffMins = Math.floor(diffMs / 60000);

        // Recente (<1 min): mostra hora:min
        if (diffMins >= 0 && diffMins < 1) {
            return this.formatWithTimeZone(dateUtc, { hour: '2-digit', minute: '2-digit' });
        }

        // Futuro
        if (diffMins < 0 && Math.abs(diffMins) < 60) {
            return `em ${Math.abs(diffMins)}min`;
        }

        // Até 59 min
        if (diffMins >= 0 && diffMins < 60) return `${diffMins}min atrás`;

        // Até 23h
        if (diffMins >= 60 && diffMins < 1440) return `${Math.floor(diffMins / 60)}h atrás`;

        // Antigos: data (ou data + hora, se preferir)
        return this.formatWithTimeZone(dateUtc, { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    formatFullDateTime(isoString) {
        if (!isoString) return 'N/A';
        const norm = this.normalizeIsoToUtc(isoString);
        const dateUtc = new Date(norm);

        const time = this.formatWithTimeZone(dateUtc, { hour: '2-digit', minute: '2-digit' });
        const date = this.formatWithTimeZone(dateUtc, { day: '2-digit', month: '2-digit', year: 'numeric' });

        // Mantém o mesmo layout que você usa
        return `${time} ${date}`;
    }

    generateTimeLabels(count) {
        const labels = [];
        const now = new Date();
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now - i * 60000);
            labels.push(time.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }));
        }
        return labels;
    }

    generateRecentTimeLabels(count) {
        const labels = [];
        const now = new Date();
        // Gerar labels de tempo com intervalo de 3 segundos (frequência de atualização)
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now - i * 3000); // 3 segundos entre cada ponto
            labels.push(time.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        }
        return labels;
    }

    generateRandomData(count, min, max) {
        return Array.from({ length: count }, () => 
            Math.random() * (max - min) + min
        );
    }

    showAlertDetails(alertId) {
        try {
            const alert = this.alertsData.find(a => a.id === alertId);
            if (!alert) {
                console.warn('Alert not found:', alertId);
                return;
            }

            // Preencher o modal com os dados do alerta
            this.safeSetTextContent('modal-title', `Alerta: ${alert.title}`);
            this.safeSetTextContent('modal-rule-name', alert.rule_name);
            this.safeSetTextContent('modal-severity', alert.severity);
            
            const severityElement = document.getElementById('modal-severity');
            if (severityElement) {
                severityElement.className = `badge badge-${alert.severity.toLowerCase()}`;
            }
            
            this.safeSetTextContent('modal-risk-score', alert.risk_score ? alert.risk_score.toFixed(4) : 'N/A');
            
            // Usar detected_at com formatação completa de data e hora
            this.safeSetTextContent('modal-detected-at', this.formatFullDateTime(alert.detected_at || alert.created_at));
            this.safeSetTextContent('modal-description', alert.description || 'Sem descrição');

            // Informações da transação
            this.safeSetTextContent('modal-tx-hash', alert.transaction_hash || 'N/A');
            this.safeSetTextContent('modal-tx-value', alert.transaction_value ? 
                `$${Number(alert.transaction_value).toLocaleString('pt-BR', {minimumFractionDigits: 2})}` : 'N/A');
            this.safeSetTextContent('modal-gas-price', alert.gas_price ? 
                `${alert.gas_price} Gwei` : 'N/A');
            this.safeSetTextContent('modal-block-number', alert.block_number || 'N/A');

            // Informações das carteiras
            this.safeSetTextContent('modal-from-address', alert.from_address || 'N/A');
            this.safeSetTextContent('modal-to-address', alert.to_address || 'N/A');
            
            // Datas de funding com formatação completa
            this.safeSetTextContent('modal-fundeddate-from', alert.fundeddate_from ? 
                this.formatFullDateTime(alert.fundeddate_from) : 'N/A');
            this.safeSetTextContent('modal-fundeddate-to', alert.fundeddate_to ? 
                this.formatFullDateTime(alert.fundeddate_to) : 'N/A');

            // Tratar seção de blacklist de forma segura
            this.handleBlacklistSection(alert);

            // Mostrar o modal
            const modal = document.getElementById('alert-modal');
            if (modal) {
                modal.style.display = 'block';
            }
        } catch (error) {
            console.error('Error showing alert details:', error);
            // Mesmo com erro, tentar mostrar o modal básico
            const modal = document.getElementById('alert-modal');
            if (modal) {
                modal.style.display = 'block';
            }
        }
    }

    safeSetTextContent(elementId, content) {
        try {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = content || 'N/A';
            }
        } catch (error) {
            console.warn(`Failed to set content for ${elementId}:`, error);
        }
    }

    handleBlacklistSection(alert) {
        try {
            // Seção de informações da blacklist (se disponível)
            const blacklistSection = document.getElementById('modal-blacklist-section');
            if ((alert.blacklist_info || alert.blacklist_infos) && alert.rule_name === 'blacklist_interaction') {
                // Remover seção existente se houver
                if (blacklistSection) {
                    blacklistSection.remove();
                }

                // Criar nova seção
                const blacklistDiv = document.createElement('div');
                blacklistDiv.id = 'modal-blacklist-section';
                blacklistDiv.className = 'alert-detail-section';

                if (alert.multiple_blacklists && alert.blacklist_infos) {
                    // Caso de múltiplos endereços blacklistados
                    let blacklistHTML = '<h3>Informações da Blacklist (Múltiplos Endereços)</h3>';
                    
                    alert.blacklist_infos.forEach((info, index) => {
                        blacklistHTML += `
                            <div class="blacklist-entry" style="margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                <h4>Endereço ${index + 1} (${info.interaction_type})</h4>
                                <div class="detail-grid">
                                    <div class="detail-item full-width">
                                        <label>Address Hash:</label>
                                        <span class="monospace">${info.address}</span>
                                    </div>
                                    <div class="detail-item">
                                        <label>Tipo:</label>
                                        <span>${info.address_type || 'N/A'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <label>Severidade:</label>
                                        <span>${info.severity_level || 'N/A'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <label>Motivo:</label>
                                        <span>${info.reason || 'N/A'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <label>Fonte:</label>
                                        <span>${info.source || 'N/A'}</span>
                                    </div>
                                    <div class="detail-item full-width">
                                        <label>Observações:</label>
                                        <span>${info.notes || 'Nenhuma observação'}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    blacklistDiv.innerHTML = blacklistHTML;
                } else if (alert.blacklist_info) {
                    // Caso de um único endereço blacklistado
                    blacklistDiv.innerHTML = `
                        <h3>Informações da Blacklist</h3>
                        <div class="detail-grid">
                            <div class="detail-item">
                                <label>Tipo:</label>
                                <span>${alert.blacklist_info.address_type || 'N/A'}</span>
                            </div>
                            <div class="detail-item">
                                <label>Severidade:</label>
                                <span>${alert.blacklist_info.severity_level || 'N/A'}</span>
                            </div>
                            <div class="detail-item">
                                <label>Motivo:</label>
                                <span>${alert.blacklist_info.reason || 'N/A'}</span>
                            </div>
                            <div class="detail-item">
                                <label>Fonte:</label>
                                <span>${alert.blacklist_info.source || 'N/A'}</span>
                            </div>
                            <div class="detail-item">
                                <label>Address Hash:</label>
                                <span class="monospace">${alert.wallet_address || 'N/A'}</span>
                            </div>
                            <div class="detail-item full-width">
                                <label>Observações:</label>
                                <span>${alert.blacklist_info.notes || 'Nenhuma observação'}</span>
                            </div>
                        </div>
                    `;
                }
                
                // Inserir após a última seção
                const modalBody = document.querySelector('#alert-modal .modal-body');
                if (modalBody) {
                    modalBody.appendChild(blacklistDiv);
                }

                // Mostrar seção
                blacklistDiv.style.display = 'block';
            } else {
                // Esconder seção de blacklist se não há informações
                if (blacklistSection) {
                    blacklistSection.style.display = 'none';
                }
            }
        } catch (error) {
            console.warn('Error handling blacklist section:', error);
        }
    }
}

// Funções globais para o modal
function closeAlertModal() {
    document.getElementById('alert-modal').style.display = 'none';
}

// Fechar modal ao clicar fora dele
window.onclick = function(event) {
    const modal = document.getElementById('alert-modal');
    if (event.target === modal) {
        closeAlertModal();
    }
}

// Fechar modal com tecla ESC
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAlertModal();
    }
});

// Inicializar dashboard quando página carregar
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new FraudDashboard();
});

// Função para limpar histórico de alertas
async function clearAlertHistory() {
    if (!confirm('Tem certeza que deseja limpar TODOS os dados (alertas + transações)?\n\nEsta ação irá:\n- Zerar todas as métricas do dashboard\n- Remover todo o histórico de alertas\n- Remover todas as transações analisadas\n\nEsta ação não pode ser desfeita.')) {
        return;
    }
    
    const button = document.getElementById('clear-history-btn');
    const originalText = button.innerHTML;
    
    try {
        // Desabilitar botão e mostrar loading
        button.disabled = true;
        button.innerHTML = '<span style="display: flex; align-items: center; gap: 0.5rem;"><div style="width: 16px; height: 16px; border: 2px solid #ffffff; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>Limpando...</span>';
        
        const response = await fetch('/api/v1/database/clear-alerts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Mostrar sucesso
            button.innerHTML = '<span style="color: #10b981;">✅ Limpo!</span>';
            
            // Recarregar dados do dashboard
            await window.dashboard.loadDashboardData();
            
            // Mostrar notificação
            showNotification('Todos os dados foram limpos com sucesso!', 'success');
            
        } else {
            throw new Error('Falha ao limpar dados');
        }
        
    } catch (error) {
        console.error('Error clearing alert history:', error);
        button.innerHTML = '<span style="color: #ef4444;">❌ Erro</span>';
        showNotification('Erro ao limpar dados do sistema', 'error');
    }
    
    // Restaurar botão após 2 segundos
    setTimeout(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    }, 2000);
}

// Função para mostrar notificações
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    // Cores baseadas no tipo
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remover notificação após 4 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 4000);
}

// Adicionar CSS para animação de atualização e notificações
const style = document.createElement('style');
style.textContent = `
    .metric-value.updated {
        animation: pulse-update 1s ease-in-out;
    }
    
    @keyframes pulse-update {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); color: #F2C744; } /* Amarelo dourado */
        100% { transform: scale(1); }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes slideIn {
        0% { transform: translateX(100%); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        0% { transform: translateX(0); opacity: 1; }
        100% { transform: translateX(100%); opacity: 0; }
    }
    
    .notification {
        transition: all 0.3s ease;
    }
`;
document.head.appendChild(style);

// Função para gerar relatório PDF
async function generatePDFReport() {
    const button = document.getElementById('generate-pdf-btn');
    const originalContent = button.innerHTML;
    
    try {
        // Mostrar loading no botão
        button.disabled = true;
        button.innerHTML = `
            <svg width="18" height="18" class="animate-spin" fill="none" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"></circle>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" class="opacity-75"></path>
            </svg>
            Gerando PDF...
        `;
        
        // Chamar API para gerar PDF
        const response = await fetch('/api/v1/reports/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Mostrar sucesso temporariamente
            button.innerHTML = `
                <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                PDF Gerado!
            `;
            
            // Mostrar notificação de sucesso
            showNotification('Relatório PDF gerado com sucesso! Download iniciado automaticamente.', 'success');
            
            // Iniciar download automaticamente
            const downloadLink = document.createElement('a');
            downloadLink.href = data.download_url;
            downloadLink.download = data.filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            // Restaurar botão após 3 segundos
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.disabled = false;
            }, 3000);
            
        } else {
            throw new Error(data.error || 'Erro ao gerar PDF');
        }
        
    } catch (error) {
        console.error('Error generating PDF report:', error);
        
        // Mostrar erro no botão
        button.innerHTML = `
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
            Erro
        `;
        
        // Mostrar notificação de erro
        showNotification('Erro ao gerar relatório PDF. Tente novamente.', 'error');
        
        // Restaurar botão após 3 segundos
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.disabled = false;
        }, 3000);
    }
}

// Adicionar animação de spin aos elementos com classe animate-spin
const spinStyle = document.createElement('style');
spinStyle.textContent = `
    .animate-spin {
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(spinStyle);
