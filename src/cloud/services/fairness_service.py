"""Fairness Service - Serviço de monitoramento de viés algorítmico."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class FairnessService:
    """
    Serviço de monitoramento contínuo de viés algorítmico.

    Responsabilidades:
    - Coletar dados de decisões (predições + ground truth)
    - Calcular métricas de fairness periodicamente
    - Alertar quando viés excede thresholds
    - Gerar relatórios de compliance (LGPD, IEEE)
    """

    def __init__(
        self,
        check_interval_hours: int = 24,
        min_samples_for_analysis: int = 100,
        alert_threshold: float = 0.10
    ):
        self.check_interval_hours = check_interval_hours
        self.min_samples = min_samples_for_analysis
        self.alert_threshold = alert_threshold

        # Dados acumulados para análise
        self._decisions: List[Dict[str, Any]] = []
        self._last_check: Optional[datetime] = None
        self._reports: List[dict] = []

        # Callbacks de alerta
        self._alert_callbacks: List[callable] = []

    def record_decision(
        self,
        prediction: int,
        ground_truth: Optional[int],
        sensitive_attr: Optional[str],
        alert_id: str,
        camera_id: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Registra decisão para análise futura de fairness.

        Args:
            prediction: Predição do modelo (0 ou 1)
            ground_truth: Label real (após validação HITL)
            sensitive_attr: Atributo sensível (ex: bairro, demografia)
            alert_id: ID do alerta
            camera_id: ID da câmera
            timestamp: Timestamp da decisão
        """
        self._decisions.append({
            "prediction": prediction,
            "ground_truth": ground_truth,
            "sensitive_attr": sensitive_attr,
            "alert_id": alert_id,
            "camera_id": camera_id,
            "timestamp": timestamp or datetime.now()
        })

        logger.debug(
            f"Decisão registrada: alert={alert_id}, pred={prediction}, "
            f"truth={ground_truth}, attr={sensitive_attr}"
        )

    def should_check_fairness(self) -> bool:
        """Verifica se é hora de análise de fairness."""
        if self._last_check is None:
            return len(self._decisions) >= self.min_samples

        hours_since_check = (datetime.now() - self._last_check).total_seconds() / 3600
        return hours_since_check >= self.check_interval_hours

    def run_fairness_analysis(self) -> Optional[dict]:
        """
        Executa análise de fairness nos dados acumulados.

        Returns:
            Relatório de fairness ou None se dados insuficientes
        """
        if len(self._decisions) < self.min_samples:
            logger.info(
                f"Dados insuficientes para análise: {len(self._decisions)} < {self.min_samples}"
            )
            return None

        # Filtra decisões com ground truth e sensitive attr
        valid_decisions = [
            d for d in self._decisions
            if d["ground_truth"] is not None and d["sensitive_attr"] is not None
        ]

        if len(valid_decisions) < self.min_samples:
            logger.info(
                f"Decisões válidas insuficientes: {len(valid_decisions)} < {self.min_samples}"
            )
            return None

        # Extrai arrays para análise
        from src.fairness.metrics import FairnessMetrics

        y_pred = [d["prediction"] for d in valid_decisions]
        y_true = [d["ground_truth"] for d in valid_decisions]
        sensitive = [d["sensitive_attr"] for d in valid_decisions]

        metrics = FairnessMetrics()
        report = metrics.generate_fairness_report(y_pred, y_true, sensitive)

        # Adiciona metadados
        report["analysis_timestamp"] = datetime.now().isoformat()
        report["samples_analyzed"] = len(valid_decisions)
        report["total_decisions"] = len(self._decisions)

        # Armazena relatório
        self._reports.append(report)
        self._last_check = datetime.now()

        # Verifica se deve alertar
        if not report["overall_passed"]:
            self._trigger_bias_alert(report)

        return report

    def register_alert_callback(self, callback: callable):
        """Registra callback para alertas de viés."""
        self._alert_callbacks.append(callback)

    def _trigger_bias_alert(self, report: dict):
        """Dispara alerta de viés detectado."""
        alert_message = (
            f"VIÉS ALGORÍTMICO DETECTADO: "
            f"FPR disparity={report['metrics']['fpr_balance']['max_disparity']:.2%}"
        )

        logger.warning(alert_message)

        for callback in self._alert_callbacks:
            try:
                callback(report, alert_message)
            except Exception as e:
                logger.error(f"Erro em callback de alerta de viés: {e}")

    def get_latest_report(self) -> Optional[dict]:
        """Retorna último relatório de fairness."""
        return self._reports[-1] if self._reports else None

    def get_historical_trends(self, metric_name: str) -> List[float]:
        """Retorna tendência histórica de uma métrica."""
        return [
            r["metrics"].get(metric_name, {}).get("max_disparity", 0)
            for r in self._reports
        ]

    def cleanup_old_data(self, max_age_days: int = 90):
        """Limpa dados antigos (retenção)."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)

        self._decisions = [
            d for d in self._decisions
            if d["timestamp"] > cutoff
        ]

        logger.info(f"Limpeza concluída: {len(self._decisions)} decisões retidas")


# Serviço global
fairness_service = FairnessService()