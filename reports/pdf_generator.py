"""
Módulo para geração de relatórios em PDF do ChimeraScan
"""
import io
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import logging

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """Gerador de relatórios PDF profissionais para o ChimeraScan"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Configurar estilos customizados para o PDF"""
        
        # Título principal
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica-Bold'
        )
        
        # Subtítulo
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        )
        
        # Cabeçalho de seção
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#059669'),
            fontName='Helvetica-Bold'
        )
        
        # Texto normal
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        )
        
        # Métricas destacadas
        self.metric_style = ParagraphStyle(
            'MetricStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica-Bold'
        )

    def generate_report(self, metrics_data: Dict, alerts_data: List[Dict], 
                       output_path: str = None) -> str:
        """
        Gera relatório completo em PDF
        
        Args:
            metrics_data: Dados das métricas do dashboard
            alerts_data: Lista de alertas recentes
            output_path: Caminho opcional para salvar o PDF
            
        Returns:
            str: Caminho do arquivo PDF gerado
        """
        try:
            # Definir nome do arquivo se não especificado
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"reports/ChimeraScan_Report_{timestamp}.pdf"
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Criar documento PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Construir conteúdo do relatório
            story = []
            
            # Cabeçalho
            story.extend(self._build_header())
            
            # Resumo executivo
            story.extend(self._build_executive_summary(metrics_data))
            
            # Métricas principais
            story.extend(self._build_metrics_section(metrics_data))
            
            # Seção de gráficos removida conforme solicitado
            
            # Alertas recentes
            story.extend(self._build_alerts_section(alerts_data))
            
            # Análise e recomendações
            story.extend(self._build_analysis_section(metrics_data, alerts_data))
            
            # Rodapé
            story.extend(self._build_footer())
            
            # Gerar PDF
            doc.build(story)
            
            logger.info(f"Relatório PDF gerado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório PDF: {e}")
            raise

    def _build_header(self) -> List:
        """Constrói o cabeçalho do relatório"""
        elements = []
        
        # Logo e título
        elements.append(Paragraph("🛡️ ChimeraScan", self.title_style))
        elements.append(Paragraph("Relatório de Detecção de Fraudes", self.subtitle_style))
        
        # Data e hora de geração
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y às %H:%M:%S")
        elements.append(Paragraph(f"<i>Gerado em {date_str}</i>", self.body_style))
        
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#059669')))
        elements.append(Spacer(1, 20))
        
        return elements

    def _build_executive_summary(self, metrics: Dict) -> List:
        """Constrói o resumo executivo"""
        elements = []
        
        elements.append(Paragraph("📊 RESUMO EXECUTIVO", self.section_style))
        
        # Cálculos para o resumo
        total_analyzed = metrics.get('transactions_analyzed', 0)
        suspicious_detected = metrics.get('suspicious_detected', 0)
        detection_rate = metrics.get('detection_rate', 0.0)
        total_alerts = metrics.get('total_alerts', 0)
        
        summary_text = f"""
        <b>Período de Análise:</b> Últimas 24 horas<br/>
        <b>Status do Sistema:</b> {metrics.get('system_status', 'N/A').upper()}<br/>
        <b>Tempo Ativo:</b> {self._format_uptime(metrics.get('uptime_seconds', 0))}<br/>
        <br/>
        <b>Resumo das Atividades:</b><br/>
        • Total de transações analisadas: <b>{total_analyzed}</b><br/>
        • Transações suspeitas detectadas: <b>{suspicious_detected}</b><br/>
        • Taxa de detecção de fraudes: <b>{detection_rate:.1f}%</b><br/>
        • Alertas gerados: <b>{total_alerts}</b><br/>
        • Alertas ativos: <b>{metrics.get('active_alerts', 0)}</b><br/>
        """
        
        elements.append(Paragraph(summary_text, self.body_style))
        elements.append(Spacer(1, 20))
        
        return elements

    def _build_metrics_section(self, metrics: Dict) -> List:
        """Constrói a seção de métricas detalhadas"""
        elements = []
        
        elements.append(Paragraph("📈 MÉTRICAS DETALHADAS", self.section_style))
        
        # Criar tabela de métricas
        data = [
            ['Métrica', 'Valor', 'Descrição'],
            ['Transações Analisadas', f"{metrics.get('transactions_analyzed', 0):,}", 'Total processado nas últimas 24h'],
            ['Transações Suspeitas', f"{metrics.get('suspicious_detected', 0):,}", 'Flagradas como potencialmente fraudulentas'],
            ['Taxa de Detecção', f"{metrics.get('detection_rate', 0.0):.1f}%", 'Percentual de detecção de suspeitas'],
            ['Alertas Totais', f"{metrics.get('total_alerts', 0):,}", 'Alertas gerados pelo sistema'],
            ['Alertas Ativos', f"{metrics.get('active_alerts', 0):,}", 'Alertas pendentes de resolução'],
            ['Alta Severidade', f"{metrics.get('high_severity_alerts', 0):,}", 'Alertas críticos que requerem atenção'],
            ['Risk Score Médio', f"{metrics.get('average_risk_score', 0.0):.3f}", 'Pontuação média de risco (0.0-1.0)'],
            ['Tempo de Resposta', '< 1s', 'Tempo médio de análise por transação'],
        ]
        
        table = Table(data, colWidths=[4*cm, 3*cm, 7*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements



    def _build_alerts_section(self, alerts: List[Dict]) -> List:
        """Constrói seção de alertas recentes"""
        elements = []
        
        elements.append(Paragraph("🚨 ALERTAS RECENTES", self.section_style))
        
        if not alerts:
            elements.append(Paragraph("Nenhum alerta registrado no período.", self.body_style))
        else:
            # Tabela de alertas
            data = [['Data/Hora', 'Hash Transação', 'Regra', 'Severidade', 'Risk Score']]
            
            for alert in alerts[:10]:  # Limitar aos 10 mais recentes
                # Formatar data com offset de -3 horas (UTC para BRT)
                created_at = alert.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        # Aplicar offset de -3 horas (UTC para BRT)
                        dt_brt = dt.replace(tzinfo=None) - timedelta(hours=3)
                        time_str = dt_brt.strftime('%d/%m %H:%M:%S')
                    except:
                        time_str = created_at[:16] if len(created_at) > 16 else created_at
                else:
                    time_str = 'N/A'
                
                # Mostrar hash completo da transação
                tx_hash = alert.get('transaction_hash', 'N/A')
                
                data.append([
                    time_str,
                    tx_hash,
                    alert.get('rule_name', 'N/A'),
                    alert.get('severity', 'N/A'),
                    f"{alert.get('risk_score', 0.0):.3f}"
                ])
            
            # Ajustar larguras das colunas para acomodar hash completo
            table = Table(data, colWidths=[2.5*cm, 4.5*cm, 3*cm, 2*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#92400e')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),  # Fonte menor para acomodar hash completo
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 20))
        return elements

    def _build_analysis_section(self, metrics: Dict, alerts: List[Dict]) -> List:
        """Constrói seção de análise e recomendações"""
        elements = []
        
        elements.append(Paragraph("🔍 ANÁLISE E RECOMENDAÇÕES", self.section_style))
        
        # Análise baseada nos dados
        detection_rate = metrics.get('detection_rate', 0.0)
        total_alerts = metrics.get('total_alerts', 0)
        high_severity = metrics.get('high_severity_alerts', 0)
        
        # Gerar recomendações baseadas nos dados
        recommendations = []
        
        if detection_rate > 50:
            recommendations.append("• <b>Alto nível de atividade suspeita detectada</b> - Revisar alertas de alta prioridade")
        elif detection_rate < 10:
            recommendations.append("• <b>Baixa atividade suspeita</b> - Sistema operando dentro dos parâmetros normais")
        
        if high_severity > 0:
            recommendations.append(f"• <b>{high_severity} alertas de alta severidade</b> - Requerem investigação imediata")
        
        if total_alerts == 0:
            recommendations.append("• <b>Nenhum alerta gerado</b> - Sistema estável ou baixo volume de transações")
        
        recommendations.append("• Manter monitoramento contínuo das métricas")
        recommendations.append("• Revisar regras de detecção periodicamente")
        
        analysis_text = f"""
        <b>Situação Atual:</b><br/>
        Com base nos dados coletados, o sistema ChimeraScan está operando com uma taxa de detecção 
        de {detection_rate:.1f}% nas últimas 24 horas.<br/>
        <br/>
        <b>Recomendações:</b><br/>
        {"<br/>".join(recommendations)}<br/>
        <br/>
        <b>Próximos Passos:</b><br/>
        • Continuar monitoramento em tempo real<br/>
        • Investigar alertas de alta prioridade<br/>
        • Documentar padrões identificados<br/>
        • Ajustar thresholds conforme necessário<br/>
        """
        
        elements.append(Paragraph(analysis_text, self.body_style))
        elements.append(Spacer(1, 20))
        
        return elements

    def _build_footer(self) -> List:
        """Constrói o rodapé do relatório"""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        elements.append(Spacer(1, 10))
        
        footer_text = f"""
        <i>Este relatório foi gerado automaticamente pelo sistema ChimeraScan.<br/>
        Para mais informações, acesse o dashboard em tempo real ou consulte a documentação técnica.<br/>
        © {datetime.now().year} ChimeraScan - Sistema de Detecção de Fraudes</i>
        """
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#6b7280')
        )
        
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements

    def _format_uptime(self, seconds: float) -> str:
        """Formata tempo de uptime em formato legível"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
