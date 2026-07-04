"""
Fairness Metrics - Métricas de justiça algorítmica para detecção comportamental.

Este módulo implementa métricas de viés algorítmico conforme:
- IEEE P7003 (Algorithmic Bias Considerations)
- NIST AI Risk Management Framework
- LGPD Artigo 20 (decisões automatizadas)

Métricas implementadas:
1. Demographic Parity - igualdade de taxa de positivos entre grupos
2. Equal Opportunity - igualdade de True Positive Rate (TPR)
3. False Positive Rate Balance - crítico para vigilância (evita discriminação)
4. Predictive Rate Parity - igualdade de valor preditivo positivo (PPV)

Uso:
    metrics = FairnessMetrics()

    # Dados de exemplo
    y_true = [1, 0, 1, 0, 1, 0, 1, 0]  # Labels reais
    y_pred = [1, 0, 1, 1, 1, 0, 0, 0]  # Predições do modelo
    sensitive_attr = ["A", "A", "A", "A", "B", "B", "B", "B"]  # Grupos

    report = metrics.generate_fairness_report(y_pred, y_true, sensitive_attr)
    print(f"Fairness passed: {report['overall_passed']}")
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

logger = logging.getLogger(__name__)


@dataclass
class FairnessResult:
    """Resultado de uma métrica de fairness."""

    metric_name: str
    group_rates: Dict[str, float]
    max_disparity: float
    passed: bool
    threshold: float = 0.10
    sample_sizes: Dict[str, int] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serializa para dict."""
        return {
            "metric_name": self.metric_name,
            "group_rates": self.group_rates,
            "max_disparity": self.max_disparity,
            "passed": self.passed,
            "threshold": self.threshold,
            "sample_sizes": self.sample_sizes,
            "details": self.details
        }


class FairnessMetrics:
    """
    Coleção de métricas de justiça algorítmica.

    Todas as métricas retornam FairnessResult com:
    - group_rates: taxa para cada grupo sensível
    - max_disparity: diferença entre maior e menor taxa
    - passed: True se disparidade < threshold (default 10%)

   _THRESHOLDs_recomendados (baseados em EEOC 4/5ths rule):
    - Demographic Parity: < 0.10 (10% disparidade)
    - Equal Opportunity: < 0.10
    - False Positive Rate: < 0.05 (mais stricto para vigilância)
    """

    def __init__(
        self,
        demographic_parity_threshold: float = 0.10,
        equal_opportunity_threshold: float = 0.10,
        fpr_threshold: float = 0.05,
        ppr_threshold: float = 0.10
    ):
        """
        Inicializa métricas de fairness.

        Args:
            demographic_parity_threshold: Threshold para paridade demográfica
            equal_opportunity_threshold: Threshold para igualdade de oportunidade
            fpr_threshold: Threshold para FPR balance (mais stricto)
            ppr_threshold: Threshold para predictive rate parity
        """
        self.thresholds = {
            "demographic_parity": demographic_parity_threshold,
            "equal_opportunity": equal_opportunity_threshold,
            "fpr_balance": fpr_threshold,
            "ppr": ppr_threshold
        }

    def demographic_parity(
        self,
        y_pred: np.ndarray,
        sensitive_attr: np.ndarray
    ) -> FairnessResult:
        """
        Paridade Demográfica (Statistical Parity).

        Mede se a taxa de predições positivas é igual entre grupos.

        Fórmula:
            P(Ŷ=1 | G=a) = P(Ŷ=1 | G=b) para todos grupos a, b

        Importante: Não considera ground truth!
        Útil para detectar viés na distribuição de alertas.

        Args:
            y_pred: Predições do modelo (0 ou 1)
            sensitive_attr: Atributo sensível (ex: gênero, raça, bairro)

        Returns:
            FairnessResult com taxas por grupo
        """
        y_pred = np.asarray(y_pred)
        sensitive_attr = np.asarray(sensitive_attr)

        groups = np.unique(sensitive_attr)
        rates = {}
        sample_sizes = {}

        for group in groups:
            mask = sensitive_attr == group
            n_positive = np.sum(y_pred[mask] == 1)
            n_total = np.sum(mask)

            rate = n_positive / n_total if n_total > 0 else 0.0
            rates[group] = rate
            sample_sizes[group] = n_total

        # Disparidade máxima
        if rates:
            max_disparity = max(rates.values()) - min(rates.values())
        else:
            max_disparity = 0.0

        threshold = self.thresholds["demographic_parity"]
        passed = max_disparity < threshold

        return FairnessResult(
            metric_name="Demographic Parity",
            group_rates=rates,
            max_disparity=max_disparity,
            passed=passed,
            threshold=threshold,
            sample_sizes=sample_sizes,
            details={
                "description": "Igualdade de taxa de predições positivas entre grupos"
            }
        )

    def equal_opportunity(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_attr: np.ndarray
    ) -> FairnessResult:
        """
        Igualdade de Oportunidade (Equalized Odds - TPR parity).

        Mede se a taxa de verdadeiros positivos (TPR) é igual entre grupos.

        Fórmula:
            P(Ŷ=1 | Y=1, G=a) = P(Ŷ=1 | Y=1, G=b)

        Importante: Apenas para casos positivos reais (Y=1).
        Crucial para garantir que o modelo detecta crimes
        igualmente bem em todos os grupos demográficos.

        Args:
            y_true: Labels reais (ground truth)
            y_pred: Predições do modelo
            sensitive_attr: Atributo sensível

        Returns:
            FairnessResult com TPR por grupo
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        sensitive_attr = np.asarray(sensitive_attr)

        groups = np.unique(sensitive_attr)
        tpr_rates = {}
        sample_sizes = {}

        for group in groups:
            # Mascara: grupo E positivo real
            group_mask = sensitive_attr == group
            positive_mask = y_true == 1
            combined_mask = group_mask & positive_mask

            n_true_positives = np.sum((y_pred[combined_mask] == 1))
            n_actual_positives = np.sum(combined_mask)

            tpr = n_true_positives / n_actual_positives if n_actual_positives > 0 else 0.0
            tpr_rates[group] = tpr
            sample_sizes[group] = n_actual_positives

        # Disparidade máxima
        if tpr_rates:
            max_disparity = max(tpr_rates.values()) - min(tpr_rates.values())
        else:
            max_disparity = 0.0

        threshold = self.thresholds["equal_opportunity"]
        passed = max_disparity < threshold

        return FairnessResult(
            metric_name="Equal Opportunity",
            group_rates=tpr_rates,
            max_disparity=max_disparity,
            passed=passed,
            threshold=threshold,
            sample_sizes=sample_sizes,
            details={
                "description": "Igualdade de taxa de detecção de positivos reais entre grupos"
            }
        )

    def false_positive_rate_balance(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_attr: np.ndarray,
        critical_threshold: float = 0.05  # Mais stricto: 5% máx disparidade
    ) -> FairnessResult:
        """
        Balanço de Falso Positivo (FPR Balance).

        Mede se a taxa de falsos positivos é igual entre grupos.

        Fórmula:
            P(Ŷ=1 | Y=0, G=a) = P(Ŷ=1 | Y=0, G=b)

        Importante: Apenas para negativos reais (Y=0).
        CRÍTICO para vigilância: FPR desigual significa que
        certos grupos são mais frequentemente falsamente
        acusados de comportamento suspeito.

        LGPD Artigo 20: Decisões automatizadas não podem
        discriminar com base em atributos sensíveis.

        Args:
            y_true: Labels reais
            y_pred: Predições do modelo
            sensitive_attr: Atributo sensível
            critical_threshold: Threshold máx disparidade (default 5% para FPR)

        Returns:
            FairnessResult com FPR por grupo
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        sensitive_attr = np.asarray(sensitive_attr)

        groups = np.unique(sensitive_attr)
        fpr_rates = {}
        sample_sizes = {}

        for group in groups:
            # Mascara: grupo E negativo real
            group_mask = sensitive_attr == group
            negative_mask = y_true == 0
            combined_mask = group_mask & negative_mask

            n_false_positives = np.sum((y_pred[combined_mask] == 1))
            n_actual_negatives = np.sum(combined_mask)

            fpr = n_false_positives / n_actual_negatives if n_actual_negatives > 0 else 0.0
            fpr_rates[group] = fpr
            sample_sizes[group] = n_actual_negatives

        # Disparidade máxima
        if fpr_rates:
            max_disparity = max(fpr_rates.values()) - min(fpr_rates.values())
        else:
            max_disparity = 0.0

        threshold = self.thresholds["fpr_balance"]
        passed = max_disparity < threshold

        return FairnessResult(
            metric_name="False Positive Rate Balance",
            group_rates=fpr_rates,
            max_disparity=max_disparity,
            passed=passed,
            threshold=threshold,
            sample_sizes=sample_sizes,
            details={
                "description": "Igualdade de taxa de falsos positivos entre grupos (CRÍTICO para vigilância)",
                "lgpd_article_20": "Decisões automatizadas devem garantir não-discriminação",
                "statistical_significance": self._check_statistical_significance(fpr_rates, sample_sizes) if all(v > 0 for v in sample_sizes.values()) else None
            }
        )

    def _check_statistical_significance(
        self,
        rates: Dict[str, float],
        sample_sizes: Dict[str, int],
        confidence_level: float = 0.95
    ) -> dict:
        """
        Verifica significância estatística das diferenças de FPR.

        Usa teste de proporção para determinar se diferenças são
        estatisticamente significativas ou apenas ruído amostral.

        Args:
            rates: Taxas de FPR por grupo
            sample_sizes: Tamanhos amostrais por grupo
            confidence_level: Nível de confiança (default 95%)

        Returns:
            Dict com resultados do teste estatístico
        """
        from scipy import stats

        groups = list(rates.keys())
        if len(groups) < 2:
            return {"note": "Insuficiente grupos para teste estatístico"}

        # Teste de proporção entre dois maiores grupos
        group1, group2 = groups[0], groups[1]
        n1, n2 = sample_sizes[group1], sample_sizes[group2]
        p1, p2 = rates[group1], rates[group2]

        # Z-test para duas proporções
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se > 0:
            z_stat = (p1 - p2) / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        else:
            z_stat = 0
            p_value = 1.0

        significant = p_value < (1 - confidence_level)

        return {
            "test": "Two-proportion Z-test",
            "groups_compared": [group1, group2],
            "z_statistic": z_stat,
            "p_value": p_value,
            "significant": significant,
            "confidence_level": confidence_level,
            "interpretation": "Diferença estatisticamente significativa" if significant else "Diferença pode ser ruído amostral"
        }

    def predictive_rate_parity(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_attr: np.ndarray
    ) -> FairnessResult:
        """
        Paridade de Taxa Preditiva (Predictive Rate Parity).

        Mede se o valor preditivo positivo (PPV) é igual entre grupos.

        Fórmula:
            P(Y=1 | Ŷ=1, G=a) = P(Y=1 | Ŷ=1, G=b)

        Importante: Apenas para predições positivas (Ŷ=1).
        Útil para garantir que alertas têm qualidade similar
        independente do grupo demographic.

        Args:
            y_true: Labels reais
            y_pred: Predições do modelo
            sensitive_attr: Atributo sensível

        Returns:
            FairnessResult com PPV por grupo
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        sensitive_attr = np.asarray(sensitive_attr)

        groups = np.unique(sensitive_attr)
        ppv_rates = {}
        sample_sizes = {}

        for group in groups:
            # Mascara: grupo E predição positiva
            group_mask = sensitive_attr == group
            pred_positive_mask = y_pred == 1
            combined_mask = group_mask & pred_positive_mask

            n_true_positives = np.sum((y_true[combined_mask] == 1))
            n_pred_positives = np.sum(combined_mask)

            ppv = n_true_positives / n_pred_positives if n_pred_positives > 0 else 0.0
            ppv_rates[group] = ppv
            sample_sizes[group] = n_pred_positives

        # Disparidade máxima
        if ppv_rates:
            max_disparity = max(ppv_rates.values()) - min(ppv_rates.values())
        else:
            max_disparity = 0.0

        threshold = self.thresholds["ppr"]
        passed = max_disparity < threshold

        return FairnessResult(
            metric_name="Predictive Rate Parity",
            group_rates=ppv_rates,
            max_disparity=max_disparity,
            passed=passed,
            threshold=threshold,
            sample_sizes=sample_sizes,
            details={
                "description": "Igualdade de precisão dos alertas positivos entre grupos"
            }
        )

    def generate_fairness_report(
        self,
        predictions: Union[List, np.ndarray],
        ground_truth: Union[List, np.ndarray],
        sensitive_attrs: Union[List, np.ndarray]
    ) -> dict:
        """
        Gera relatório completo de fairness.

        Executa todas as 4 métricas e retorna relatório consolidado.

        Args:
            predictions: Predições do modelo
            ground_truth: Labels reais (ground truth)
            sensitive_attrs: Atributos sensíveis (ex: gênero, raça, bairro)

        Returns:
            Dict com:
            - overall_passed: True se todas métricas passaram
            - metrics: Dict com resultados de cada métrica
            - recommendations: Lista de recomendações
            - sample_size: Total de amostras
            - group_distribution: Distribuição de grupos
        """
        y_pred = np.asarray(predictions)
        y_true = np.asarray(ground_truth)
        sens = np.asarray(sensitive_attrs)

        # Executa todas métricas
        results = {
            "demographic_parity": self.demographic_parity(y_pred, sens),
            "equal_opportunity": self.equal_opportunity(y_true, y_pred, sens),
            "fpr_balance": self.false_positive_rate_balance(y_true, y_pred, sens),
            "predictive_rate_parity": self.predictive_rate_parity(y_true, y_pred, sens)
        }

        # Verifica overall
        overall_passed = all(r.passed for r in results.values())

        # Gera recomendações
        recommendations = self._generate_recommendations(results)

        # Distribuição de grupos
        groups, counts = np.unique(sens, return_counts=True)
        group_distribution = dict(zip(groups, counts))

        return {
            "overall_passed": overall_passed,
            "metrics": {k: v.to_dict() for k, v in results.items()},
            "recommendations": recommendations,
            "sample_size": len(y_pred),
            "group_distribution": group_distribution,
            "thresholds_used": self.thresholds
        }

    def _generate_recommendations(self, results: Dict[str, FairnessResult]) -> List[str]:
        """Gera recomendações baseadas nos resultados."""
        recommendations = []

        for metric_name, result in results.items():
            if not result.passed:
                if metric_name == "demographic_parity":
                    recommendations.append(
                        f"Viés em Demographic Parity: disparidade {result.max_disparity:.2%} > "
                        f"{result.threshold:.0%}. Revise threshold de alarme ou balanceie dataset."
                    )
                elif metric_name == "equal_opportunity":
                    recommendations.append(
                        f"Viés em Equal Opportunity: disparidade {result.max_disparity:.2%} > "
                        f"{result.threshold:.0%}. Modelo pode estar sub-detectando crimes em certos grupos."
                    )
                elif metric_name == "fpr_balance":
                    recommendations.append(
                        f"VIÉS CRÍTICO em False Positive Rate: disparidade {result.max_disparity:.2%} > "
                        f"{result.threshold:.0%}. Certos grupos têm mais falsos positivos - risco de discriminação!"
                    )
                elif metric_name == "predictive_rate_parity":
                    recommendations.append(
                        f"Viés em Predictive Rate Parity: disparidade {result.max_disparity:.2%} > "
                        f"{result.threshold:.0%}. Qualidade dos alertas varia entre grupos."
                    )

        if not recommendations:
            recommendations.append(
                "Todas métricas de fairness dentro dos thresholds. Continue monitorando."
            )

        return recommendations


class BiasDetector:
    """
    Detector contínuo de viés em produção.

    Monitora métricas de fairness ao longo do tempo
    e alerta quando disparidade excede thresholds.

    Uso:
        detector = BiasDetector(window_size=1000)  # Janela de 1000 predições

        # Registra predição
        detector.record(
            prediction=1,
            ground_truth=0,
            sensitive_attr="group_A"
        )

        # Verifica viés periodicamente
        report = detector.check_bias()
        if not report["overall_passed"]:
            alert_operators(report)
    """

    def __init__(
        self,
        window_size: int = 1000,
        check_interval: int = 100
    ):
        """
        Inicializa detector de viés.

        Args:
            window_size: Tamanho da janela de análise (amostras)
            check_interval: Verifica bias a cada N amostras
        """
        self.window_size = window_size
        self.check_interval = check_interval

        # Buffers circulares
        self._predictions: List = []
        self._ground_truth: List = []
        self._sensitive_attrs: List = []

        # Métricas
        self.metrics = FairnessMetrics()

        # Contador
        self._sample_count = 0
        self._last_check = 0

        # Histórico de reports
        self._reports: List[dict] = []

    def record(
        self,
        prediction: int,
        ground_truth: int,
        sensitive_attr: Any
    ):
        """
        Registra predição para análise futura.

        Args:
            prediction: Predição do modelo (0 ou 1)
            ground_truth: Label real (0 ou 1)
            sensitive_attr: Grupo sensível (ex: "male", "female", "other")
        """
        # Adiciona aos buffers
        self._predictions.append(prediction)
        self._ground_truth.append(ground_truth)
        self._sensitive_attrs.append(sensitive_attr)

        self._sample_count += 1

        # Mantém window_size máximo
        if len(self._predictions) > self.window_size:
            self._predictions.pop(0)
            self._ground_truth.pop(0)
            self._sensitive_attrs.pop(0)

    def check_bias(self) -> Optional[dict]:
        """
        Verifica viés nas últimas N amostras.

        Returns:
            Relatório de fairness ou None se amostras insuficientes
        """
        # Verifica se tem amostras suficientes
        if len(self._predictions) < self.window_size // 10:
            logger.debug("Amostras insuficientes para análise de bias")
            return None

        # Converte arrays
        y_pred = np.array(self._predictions)
        y_true = np.array(self._ground_truth)
        sens = np.array(self._sensitive_attrs)

        # Gera relatório
        report = self.metrics.generate_fairness_report(y_pred, y_true, sens)
        report["check_timestamp"] = datetime.now().isoformat()
        report["samples_analyzed"] = len(self._predictions)

        # Armazena histórico
        self._reports.append(report)

        self._last_check = self._sample_count

        return report

    def should_check(self) -> bool:
        """Verifica se é hora de analisar bias."""
        return (self._sample_count - self._last_check) >= self.check_interval

    def get_historical_trend(self, metric_name: str) -> List[float]:
        """
        Retorna tendência histórica de uma métrica.

        Args:
            metric_name: Nome da métrica (ex: "fpr_balance")

        Returns:
            Lista de max_disparity ao longo do tempo
        """
        return [
            r["metrics"][metric_name]["max_disparity"]
            for r in self._reports
            if metric_name in r["metrics"]
        ]


# Import necessário para BiasDetector
from datetime import datetime