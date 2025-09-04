"""
Advanced Pattern Analyzers
Implementa análise avançada de padrões temporais e de volume para wash trading
"""
import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from scipy import stats
import math

from interfaces.wash_trading import ITemporalPatternAnalyzer, IVolumeAnalyzer
from data.models import TransactionData

logger = logging.getLogger(__name__)

@dataclass
class TemporalPattern:
    """Representa um padrão temporal detectado"""
    pattern_type: str
    regularity_score: float
    frequency_analysis: Dict[str, float]
    time_clustering: Dict[str, Any]
    anomaly_score: float
    confidence: float

@dataclass
class VolumePattern:
    """Representa um padrão de volume detectado"""
    pattern_type: str
    similarity_score: float
    clustering_analysis: Dict[str, Any]
    round_number_score: float
    preservation_analysis: Dict[str, Any]
    anomaly_score: float
    confidence: float

class AdvancedTemporalAnalyzer(ITemporalPatternAnalyzer):
    """
    Analisador avançado de padrões temporais
    
    Implementa algoritmos sofisticados para detectar:
    - Regularidade temporal suspeita
    - Clustering de timestamps
    - Análise de frequência
    - Detecção de anomalias temporais
    - Padrões de horário específico
    
    Utiliza técnicas de:
    - Análise estatística (scipy.stats)
    - Clustering temporal
    - Fourier Transform para padrões periódicos
    - Análise estatística avançada para detecção de anomalias
    """
    
    def __init__(self):
        self.analysis_cache: Dict[str, TemporalPattern] = {}
        self.cache_ttl = timedelta(minutes=15)
        self.stats = {
            "patterns_analyzed": 0,
            "regularities_detected": 0,
            "anomalies_detected": 0
        }
        
        logger.info("AdvancedTemporalAnalyzer initialized with statistical analysis capabilities")
    
    async def analyze_timing_patterns(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """
        Análise avançada de padrões temporais usando multiple técnicas
        
        Returns:
            Análise completa com scores de confiança e detalhes dos padrões
        """
        if len(transactions) < 3:
            return {
                "pattern_detected": False,
                "reason": "insufficient_data",
                "minimum_required": 3
            }
        
        try:
            # Extrair timestamps
            timestamps = [tx.timestamp for tx in transactions]
            timestamps.sort()
            
            # 1. Análise de Regularidade Avançada
            regularity_analysis = await self._analyze_regularity_advanced(timestamps)
            
            # 2. Análise de Clustering Temporal
            clustering_analysis = await self._analyze_temporal_clustering(timestamps)
            
            # 3. Análise de Frequência (Fourier-based)
            frequency_analysis = await self._analyze_frequency_patterns(timestamps)
            
            # 4. Detecção de Anomalias Temporais
            anomaly_analysis = await self._detect_temporal_anomalies(timestamps)
            
            # 5. Análise de Horários Suspeitos
            time_of_day_analysis = await self._analyze_time_of_day_patterns(timestamps)
            
            # Combinar análises para score geral
            overall_confidence = self._calculate_temporal_confidence([
                regularity_analysis,
                clustering_analysis,
                frequency_analysis,
                anomaly_analysis,
                time_of_day_analysis
            ])
            
            pattern_detected = overall_confidence > 0.7
            
            result = {
                "pattern_detected": pattern_detected,
                "overall_confidence": overall_confidence,
                "regularity_analysis": regularity_analysis,
                "clustering_analysis": clustering_analysis,
                "frequency_analysis": frequency_analysis,
                "anomaly_analysis": anomaly_analysis,
                "time_of_day_analysis": time_of_day_analysis,
                "transaction_count": len(transactions),
                "time_span_hours": (timestamps[-1] - timestamps[0]).total_seconds() / 3600,
                "analysis_method": "advanced_statistical"
            }
            
            self.stats["patterns_analyzed"] += 1
            if pattern_detected:
                self.stats["regularities_detected"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error in advanced temporal analysis: {e}")
            return {
                "pattern_detected": False,
                "error": str(e),
                "analysis_method": "advanced_statistical"
            }
    
    async def detect_regular_intervals(self, 
                                     transactions: List[TransactionData], 
                                     tolerance_seconds: int = 300) -> Dict[str, Any]:
        """
        Detecção avançada de intervalos regulares usando análise estatística
        """
        if len(transactions) < 4:
            return {"regular_intervals_detected": False, "reason": "insufficient_data"}
        
        timestamps = sorted([tx.timestamp for tx in transactions])
        intervals = []
        
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return {"regular_intervals_detected": False, "reason": "no_intervals"}
        
        # Análise estatística dos intervalos
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        median_interval = np.median(intervals)
        
        # Coeficiente de variação (menor = mais regular)
        cv = std_interval / mean_interval if mean_interval > 0 else float('inf')
        
        # Test de normalidade (intervalos regulares seguem distribuição normal)
        if len(intervals) >= 8:
            try:
                shapiro_stat, shapiro_p = stats.shapiro(intervals)
                normality_score = shapiro_p
            except:
                normality_score = 0.0
        else:
            normality_score = 0.0
        
        # Score de regularidade combinado
        regularity_score = max(0, min(1, (1 - cv) * 0.7 + normality_score * 0.3))
        
        # Detectar intervalos específicos
        common_intervals = self._find_common_intervals(intervals, tolerance_seconds)
        
        is_regular = regularity_score > 0.8 and cv < 0.3
        
        return {
            "regular_intervals_detected": is_regular,
            "regularity_score": regularity_score,
            "coefficient_of_variation": cv,
            "mean_interval_seconds": mean_interval,
            "median_interval_seconds": median_interval,
            "std_deviation_seconds": std_interval,
            "normality_score": normality_score,
            "common_intervals": common_intervals,
            "tolerance_seconds": tolerance_seconds,
            "interval_count": len(intervals)
        }
    
    async def _analyze_regularity_advanced(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Análise avançada de regularidade usando múltiplas métricas"""
        intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                    for i in range(1, len(timestamps))]
        
        if not intervals:
            return {"score": 0.0, "method": "no_intervals"}
        
        # Múltiplas métricas de regularidade
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        cv = std_interval / mean_interval if mean_interval > 0 else float('inf')
        
        # Autocorrelação (mede periodicidade)
        if len(intervals) > 5:
            autocorr = np.corrcoef(intervals[:-1], intervals[1:])[0,1] if len(set(intervals)) > 1 else 0
            autocorr = 0 if np.isnan(autocorr) else autocorr
        else:
            autocorr = 0
        
        # Score composto
        regularity_score = max(0, min(1, (1 - min(cv, 2)) * 0.6 + abs(autocorr) * 0.4))
        
        return {
            "score": regularity_score,
            "coefficient_variation": cv,
            "autocorrelation": autocorr,
            "mean_interval": mean_interval,
            "std_interval": std_interval,
            "method": "advanced_statistical"
        }
    
    async def _analyze_temporal_clustering(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Análise de clustering temporal usando algoritmo K-means adaptado"""
        if len(timestamps) < 4:
            return {"clustering_detected": False, "reason": "insufficient_data"}
        
        # Converter para segundos desde primeiro timestamp
        base_time = timestamps[0]
        time_points = [(ts - base_time).total_seconds() for ts in timestamps]
        
        # Análise de clustering simples baseada em distância
        time_points.sort()
        gaps = [time_points[i+1] - time_points[i] for i in range(len(time_points)-1)]
        
        if not gaps:
            return {"clustering_detected": False, "reason": "no_gaps"}
        
        # Identificar gaps significativos (outliers)
        mean_gap = np.mean(gaps)
        std_gap = np.std(gaps)
        threshold = mean_gap + 2 * std_gap
        
        large_gaps = [gap for gap in gaps if gap > threshold]
        cluster_count = len(large_gaps) + 1
        
        # Score de clustering (mais clusters = mais suspeito para wash trading)
        if cluster_count > len(timestamps) * 0.3:  # Muitos clusters pequenos
            clustering_score = 0.8
        elif cluster_count >= 3:  # Alguns clusters
            clustering_score = 0.6
        else:  # Poucos clusters
            clustering_score = 0.3
        
        return {
            "clustering_detected": cluster_count >= 3,
            "clustering_score": clustering_score,
            "cluster_count": cluster_count,
            "large_gaps_count": len(large_gaps),
            "mean_gap_seconds": mean_gap,
            "largest_gap_seconds": max(gaps) if gaps else 0,
            "method": "gap_based_clustering"
        }
    
    async def _analyze_frequency_patterns(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Análise de frequência usando transformada de Fourier simplificada"""
        if len(timestamps) < 8:
            return {"frequency_patterns": False, "reason": "insufficient_data"}
        
        # Converter para série temporal
        base_time = timestamps[0]
        time_series = [(ts - base_time).total_seconds() / 3600 for ts in timestamps]  # Horas
        
        # Calcular intervalos
        intervals = [time_series[i+1] - time_series[i] for i in range(len(time_series)-1)]
        
        if len(intervals) < 4:
            return {"frequency_patterns": False, "reason": "insufficient_intervals"}
        
        # Análise de periodicidade simples
        # Procurar por padrões repetitivos nos intervalos
        interval_counts = defaultdict(int)
        for interval in intervals:
            # Agrupar intervalos similares (tolerance de 10 minutos)
            rounded_interval = round(interval * 6) / 6  # Grupos de 10 min
            interval_counts[rounded_interval] += 1
        
        # Encontrar intervalo mais comum
        most_common_interval = max(interval_counts.items(), key=lambda x: x[1])
        repetition_ratio = most_common_interval[1] / len(intervals)
        
        # Score baseado na repetição
        frequency_score = min(1.0, repetition_ratio * 2)  # 50%+ repetição = score alto
        
        return {
            "frequency_patterns": frequency_score > 0.6,
            "frequency_score": frequency_score,
            "most_common_interval_hours": most_common_interval[0],
            "repetition_ratio": repetition_ratio,
            "unique_intervals": len(interval_counts),
            "method": "simple_frequency_analysis"
        }
    
    async def _detect_temporal_anomalies(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Detecta anomalias temporais usando análise estatística"""
        if len(timestamps) < 5:
            return {"anomalies_detected": False, "reason": "insufficient_data"}
        
        # Analisar intervalos entre transações
        intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                    for i in range(1, len(timestamps))]
        
        if not intervals:
            return {"anomalies_detected": False, "reason": "no_intervals"}
        
        # Estatísticas dos intervalos
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Detectar outliers usando regra 3-sigma
        anomalies = []
        for i, interval in enumerate(intervals):
            z_score = abs(interval - mean_interval) / std_interval if std_interval > 0 else 0
            if z_score > 2.5:  # Mais de 2.5 desvios padrão
                anomalies.append({
                    "index": i,
                    "interval_seconds": interval,
                    "z_score": z_score,
                    "timestamp": timestamps[i+1].isoformat()
                })
        
        # Score de anomalia
        anomaly_ratio = len(anomalies) / len(intervals)
        anomaly_score = min(1.0, anomaly_ratio * 3)  # Normalizar
        
        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomaly_score": anomaly_score,
            "anomaly_count": len(anomalies),
            "anomaly_ratio": anomaly_ratio,
            "anomalies": anomalies[:5],  # Primeiros 5 para não sobrecarregar
            "mean_interval_seconds": mean_interval,
            "std_interval_seconds": std_interval,
            "method": "statistical_outlier_detection"
        }
    
    async def _analyze_time_of_day_patterns(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Analisa padrões de horário do dia"""
        if len(timestamps) < 3:
            return {"time_patterns": False, "reason": "insufficient_data"}
        
        # Agrupar por hora do dia
        hour_counts = defaultdict(int)
        for ts in timestamps:
            hour = ts.hour
            hour_counts[hour] += 1
        
        # Calcular distribuição
        total = len(timestamps)
        hour_distribution = {hour: count/total for hour, count in hour_counts.items()}
        
        # Detectar concentração em horários específicos
        max_hour_ratio = max(hour_distribution.values()) if hour_distribution else 0
        
        # Horários off-hours (22:00-06:00) são mais suspeitos
        off_hours_count = sum(count for hour, count in hour_counts.items() 
                             if hour >= 22 or hour <= 6)
        off_hours_ratio = off_hours_count / total
        
        # Score baseado em concentração e off-hours
        concentration_score = max_hour_ratio * 2  # Alta concentração = suspeito
        off_hours_score = off_hours_ratio * 1.5   # Off-hours = suspeito
        
        pattern_score = min(1.0, (concentration_score + off_hours_score) / 2)
        
        return {
            "time_patterns": pattern_score > 0.4,
            "pattern_score": pattern_score,
            "max_hour_concentration": max_hour_ratio,
            "off_hours_ratio": off_hours_ratio,
            "hour_distribution": dict(hour_distribution),
            "most_active_hour": max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None,
            "method": "time_of_day_analysis"
        }
    
    def _calculate_temporal_confidence(self, analyses: List[Dict[str, Any]]) -> float:
        """Calcula confiança geral combinando múltiplas análises"""
        scores = []
        weights = [0.3, 0.2, 0.2, 0.2, 0.1]  # Pesos para diferentes análises
        
        for analysis, weight in zip(analyses, weights):
            if isinstance(analysis, dict):
                # Extrair score principal de cada análise
                if "score" in analysis:
                    scores.append(analysis["score"] * weight)
                elif "clustering_score" in analysis:
                    scores.append(analysis["clustering_score"] * weight)
                elif "frequency_score" in analysis:
                    scores.append(analysis["frequency_score"] * weight)
                elif "anomaly_score" in analysis:
                    scores.append(analysis["anomaly_score"] * weight)
                elif "pattern_score" in analysis:
                    scores.append(analysis["pattern_score"] * weight)
        
        return sum(scores) if scores else 0.0
    
    def _find_common_intervals(self, intervals: List[float], tolerance: int) -> List[Dict[str, Any]]:
        """Encontra intervalos comuns com tolerância"""
        interval_groups = defaultdict(list)
        
        for interval in intervals:
            # Agrupar intervalos similares
            group_key = round(interval / tolerance) * tolerance
            interval_groups[group_key].append(interval)
        
        # Retornar grupos com mais de 1 elemento
        common = []
        for group_key, group_intervals in interval_groups.items():
            if len(group_intervals) > 1:
                common.append({
                    "target_interval_seconds": group_key,
                    "actual_intervals": group_intervals,
                    "count": len(group_intervals),
                    "avg_deviation": np.std(group_intervals)
                })
        
        return sorted(common, key=lambda x: x["count"], reverse=True)

class AdvancedVolumeAnalyzer(IVolumeAnalyzer):
    """
    Analisador avançado de padrões de volume
    
    Implementa análise sofisticada de:
    - Similaridade de valores usando análise estatística
    - Clustering de volumes
    - Detecção de números redondos
    - Preservação de volume em caminhos
    - Análise de distribuição estatística
    """
    
    def __init__(self):
        self.analysis_cache: Dict[str, VolumePattern] = {}
        self.stats = {
            "volumes_analyzed": 0,
            "similarities_detected": 0,
            "round_numbers_detected": 0
        }
        
        logger.info("AdvancedVolumeAnalyzer initialized")
    
    async def analyze_value_similarity(self, 
                                     transactions: List[TransactionData], 
                                     similarity_threshold: float = 0.95) -> Dict[str, Any]:
        """
        Análise avançada de similaridade de valores usando multiple técnicas
        """
        if len(transactions) < 3:
            return {"similarity_detected": False, "reason": "insufficient_data"}
        
        values = [tx.value for tx in transactions]
        
        try:
            # 1. Análise Estatística Básica
            basic_stats = await self._calculate_basic_value_stats(values)
            
            # 2. Clustering de Valores
            clustering_analysis = await self._analyze_value_clustering(values)
            
            # 3. Detecção de Números Redondos
            round_number_analysis = await self._detect_round_numbers(values)
            
            # 4. Análise de Distribuição
            distribution_analysis = await self._analyze_value_distribution(values)
            
            # 5. Padrões de Similaridade Específicos
            similarity_patterns = await self._detect_similarity_patterns(values)
            
            # Combinar análises
            overall_similarity_score = self._calculate_volume_confidence([
                basic_stats,
                clustering_analysis,
                round_number_analysis,
                distribution_analysis,
                similarity_patterns
            ])
            
            similarity_detected = overall_similarity_score >= similarity_threshold
            
            result = {
                "similarity_detected": similarity_detected,
                "overall_similarity_score": overall_similarity_score,
                "basic_stats": basic_stats,
                "clustering_analysis": clustering_analysis,
                "round_number_analysis": round_number_analysis,
                "distribution_analysis": distribution_analysis,
                "similarity_patterns": similarity_patterns,
                "threshold_used": similarity_threshold,
                "value_count": len(values),
                "analysis_method": "advanced_statistical"
            }
            
            self.stats["volumes_analyzed"] += 1
            if similarity_detected:
                self.stats["similarities_detected"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error in advanced volume analysis: {e}")
            return {
                "similarity_detected": False,
                "error": str(e),
                "analysis_method": "advanced_statistical"
            }
    
    async def detect_volume_preservation(self, 
                                       transaction_path: List[TransactionData], 
                                       preservation_threshold: float = 0.90) -> Dict[str, Any]:
        """
        Análise avançada de preservação de volume em caminhos de transação
        """
        if len(transaction_path) < 2:
            return {"preservation_detected": False, "reason": "insufficient_path_length"}
        
        values = [tx.value for tx in transaction_path]
        
        try:
            # Análise de preservação ao longo do caminho
            preservation_ratios = []
            cumulative_loss = 0.0
            
            for i in range(1, len(values)):
                ratio = values[i] / values[0] if values[0] > 0 else 0
                preservation_ratios.append(ratio)
                
                loss = values[0] - values[i]
                cumulative_loss += loss
            
            # Final preservation ratio
            final_preservation = values[-1] / values[0] if values[0] > 0 else 0
            
            # Análise de padrão de perda
            loss_pattern = await self._analyze_loss_pattern(values)
            
            # Detecção de preservação artificial
            artificial_preservation = await self._detect_artificial_preservation(values)
            
            result = {
                "preservation_detected": final_preservation >= preservation_threshold,
                "final_preservation_ratio": final_preservation,
                "preservation_ratios": preservation_ratios,
                "cumulative_loss": cumulative_loss,
                "initial_value": values[0],
                "final_value": values[-1],
                "total_value_lost": values[0] - values[-1],
                "loss_pattern": loss_pattern,
                "artificial_preservation": artificial_preservation,
                "preservation_threshold": preservation_threshold,
                "path_length": len(transaction_path),
                "analysis_method": "advanced_preservation"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in volume preservation analysis: {e}")
            return {
                "preservation_detected": False,
                "error": str(e),
                "analysis_method": "advanced_preservation"
            }
    
    async def _calculate_basic_value_stats(self, values: List[float]) -> Dict[str, float]:
        """Calcula estatísticas básicas dos valores"""
        if not values:
            return {"similarity_score": 0.0}
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        median_val = np.median(values)
        
        # Coeficiente de variação (menor = mais similar)
        cv = std_val / mean_val if mean_val > 0 else float('inf')
        
        # Score de similaridade baseado em CV
        similarity_score = max(0, min(1, 1 - cv))
        
        return {
            "similarity_score": similarity_score,
            "coefficient_variation": cv,
            "mean_value": mean_val,
            "std_deviation": std_val,
            "median_value": median_val,
            "min_value": min(values),
            "max_value": max(values),
            "method": "basic_statistics"
        }
    
    async def _analyze_value_clustering(self, values: List[float]) -> Dict[str, Any]:
        """Análise de clustering de valores"""
        if len(values) < 4:
            return {"clustering_detected": False, "reason": "insufficient_data"}
        
        # Clustering simples baseado em proximidade
        sorted_values = sorted(values)
        
        # Encontrar gaps significativos
        gaps = [sorted_values[i+1] - sorted_values[i] for i in range(len(sorted_values)-1)]
        
        if not gaps:
            return {"clustering_detected": False, "reason": "no_gaps"}
        
        mean_gap = np.mean(gaps)
        std_gap = np.std(gaps)
        
        # Identificar gaps grandes (outliers)
        threshold = mean_gap + 1.5 * std_gap
        large_gaps = [gap for gap in gaps if gap > threshold]
        
        cluster_count = len(large_gaps) + 1
        
        # Clusters pequenos e densos são mais suspeitos
        avg_cluster_size = len(values) / cluster_count
        density_score = min(1.0, avg_cluster_size / 3.0)  # 3+ per cluster = dense
        
        clustering_score = density_score if cluster_count >= 2 else 0.0
        
        return {
            "clustering_detected": cluster_count >= 2 and density_score > 0.5,
            "clustering_score": clustering_score,
            "cluster_count": cluster_count,
            "avg_cluster_size": avg_cluster_size,
            "large_gaps_count": len(large_gaps),
            "density_score": density_score,
            "method": "gap_based_clustering"
        }
    
    async def _detect_round_numbers(self, values: List[float]) -> Dict[str, Any]:
        """Detecta números redondos suspeitos"""
        if not values:
            return {"round_numbers_detected": False, "reason": "no_values"}
        
        round_thresholds = [1000, 5000, 10000, 50000, 100000]
        round_count = 0
        round_details = []
        
        for value in values:
            for threshold in round_thresholds:
                if value % threshold == 0:
                    round_count += 1
                    round_details.append({
                        "value": value,
                        "round_to": threshold
                    })
                    break  # Contar apenas o maior threshold
        
        round_ratio = round_count / len(values)
        round_score = min(1.0, round_ratio * 2)  # 50%+ números redondos = score alto
        
        # Verificar números "quase redondos" (terminam em 00, 000, etc.)
        quasi_round_count = 0
        for value in values:
            str_value = str(int(value))
            if str_value.endswith('00') or str_value.endswith('000'):
                quasi_round_count += 1
        
        quasi_round_ratio = quasi_round_count / len(values)
        final_score = max(round_score, quasi_round_ratio * 1.5)
        
        self.stats["round_numbers_detected"] += round_count
        
        return {
            "round_numbers_detected": round_ratio > 0.3,  # 30%+ números redondos
            "round_score": final_score,
            "round_count": round_count,
            "round_ratio": round_ratio,
            "quasi_round_count": quasi_round_count,
            "quasi_round_ratio": quasi_round_ratio,
            "round_details": round_details[:5],  # Primeiros 5
            "method": "round_number_detection"
        }
    
    async def _analyze_value_distribution(self, values: List[float]) -> Dict[str, Any]:
        """Analisa distribuição estatística dos valores"""
        if len(values) < 5:
            return {"distribution_analysis": False, "reason": "insufficient_data"}
        
        try:
            # Test de normalidade
            if len(values) >= 8:
                shapiro_stat, shapiro_p = stats.shapiro(values)
                normality_score = shapiro_p
            else:
                normality_score = 0.0
            
            # Análise de skewness e kurtosis
            skewness = stats.skew(values)
            kurtosis_val = stats.kurtosis(values)
            
            # Valores muito similares tendem a ter distribuição "pontuda" (high kurtosis)
            # e baixo skewness
            similarity_from_distribution = 0.0
            
            if abs(skewness) < 0.5:  # Baixo skew
                similarity_from_distribution += 0.3
            
            if kurtosis_val > 1:  # Alta curtose (valores concentrados)
                similarity_from_distribution += 0.4
            
            if normality_score > 0.1:  # Distribuição normal
                similarity_from_distribution += 0.3
            
            return {
                "distribution_analysis": similarity_from_distribution > 0.5,
                "distribution_score": similarity_from_distribution,
                "normality_score": normality_score,
                "skewness": skewness,
                "kurtosis": kurtosis_val,
                "shapiro_statistic": shapiro_stat if len(values) >= 8 else None,
                "method": "statistical_distribution"
            }
            
        except Exception as e:
            return {
                "distribution_analysis": False,
                "error": str(e),
                "method": "statistical_distribution"
            }
    
    async def _detect_similarity_patterns(self, values: List[float]) -> Dict[str, Any]:
        """Detecta padrões específicos de similaridade"""
        if len(values) < 3:
            return {"patterns_detected": False, "reason": "insufficient_data"}
        
        patterns = {
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "arithmetic_progression": False,
            "geometric_progression": False,
            "percentage_based": False
        }
        
        # Duplicatas exatas
        unique_values = set(values)
        patterns["exact_duplicates"] = len(values) - len(unique_values)
        
        # Duplicatas próximas (±1% de diferença)
        tolerance = 0.01  # 1%
        near_duplicate_count = 0
        
        for i in range(len(values)):
            for j in range(i+1, len(values)):
                diff_ratio = abs(values[i] - values[j]) / max(values[i], values[j])
                if diff_ratio <= tolerance:
                    near_duplicate_count += 1
        
        patterns["near_duplicates"] = near_duplicate_count
        
        # Progressão aritmética (diferenças constantes)
        if len(values) >= 4:
            sorted_vals = sorted(values)
            diffs = [sorted_vals[i+1] - sorted_vals[i] for i in range(len(sorted_vals)-1)]
            if len(set([round(d, 2) for d in diffs])) <= 2:  # Máximo 2 diferenças distintas
                patterns["arithmetic_progression"] = True
        
        # Score combinado
        pattern_score = 0.0
        
        if patterns["exact_duplicates"] > len(values) * 0.3:
            pattern_score += 0.4
        
        if patterns["near_duplicates"] > len(values) * 0.2:
            pattern_score += 0.3
        
        if patterns["arithmetic_progression"]:
            pattern_score += 0.3
        
        return {
            "patterns_detected": pattern_score > 0.4,
            "pattern_score": pattern_score,
            **patterns,
            "method": "similarity_patterns"
        }
    
    async def _analyze_loss_pattern(self, values: List[float]) -> Dict[str, Any]:
        """Analisa padrão de perda de valor ao longo do caminho"""
        if len(values) < 2:
            return {"pattern": "insufficient_data"}
        
        losses = [values[0] - values[i] for i in range(1, len(values))]
        
        # Classificar padrão de perda
        if all(loss <= values[0] * 0.05 for loss in losses):  # ≤5% loss
            pattern = "minimal_loss"
            suspicion_score = 0.9
        elif all(loss <= values[0] * 0.1 for loss in losses):  # ≤10% loss
            pattern = "low_loss"
            suspicion_score = 0.7
        elif all(loss > values[0] * 0.5 for loss in losses):  # >50% loss
            pattern = "high_loss"
            suspicion_score = 0.1
        else:
            pattern = "variable_loss"
            suspicion_score = 0.4
        
        return {
            "pattern": pattern,
            "suspicion_score": suspicion_score,
            "losses": losses,
            "max_loss": max(losses) if losses else 0,
            "avg_loss": np.mean(losses) if losses else 0
        }
    
    async def _detect_artificial_preservation(self, values: List[float]) -> Dict[str, Any]:
        """Detecta preservação artificial de volume"""
        if len(values) < 3:
            return {"artificial_detected": False, "reason": "insufficient_data"}
        
        # Padrões suspeitos de preservação artificial:
        # 1. Perda muito pequena e consistente
        # 2. Recuperação de valor no final
        # 3. Valores "muito perfeitos"
        
        initial_value = values[0]
        final_value = values[-1]
        min_value = min(values)
        
        # Recuperação suspeita
        recovery_ratio = final_value / min_value if min_value > 0 else 0
        
        # Preservação muito alta
        preservation = final_value / initial_value if initial_value > 0 else 0
        
        artificial_score = 0.0
        
        if preservation > 0.98:  # >98% preservação
            artificial_score += 0.4
        
        if recovery_ratio > 1.5:  # Recuperou 50%+ do valor mínimo
            artificial_score += 0.3
        
        # Valores "muito redondos" no final
        if final_value % 1000 == 0 or final_value % 500 == 0:
            artificial_score += 0.3
        
        return {
            "artificial_detected": artificial_score > 0.5,
            "artificial_score": artificial_score,
            "recovery_ratio": recovery_ratio,
            "preservation_ratio": preservation,
            "min_value_in_path": min_value,
            "method": "artificial_pattern_detection"
        }
    
    def _calculate_volume_confidence(self, analyses: List[Dict[str, Any]]) -> float:
        """Calcula confiança geral combinando análises de volume"""
        scores = []
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]  # Pesos para diferentes análises
        
        for analysis, weight in zip(analyses, weights):
            if isinstance(analysis, dict):
                # Extrair score principal de cada análise
                score = 0.0
                if "similarity_score" in analysis:
                    score = analysis["similarity_score"]
                elif "clustering_score" in analysis:
                    score = analysis["clustering_score"]
                elif "round_score" in analysis:
                    score = analysis["round_score"]
                elif "distribution_score" in analysis:
                    score = analysis["distribution_score"]
                elif "pattern_score" in analysis:
                    score = analysis["pattern_score"]
                
                scores.append(score * weight)
        
        return sum(scores) if scores else 0.0
