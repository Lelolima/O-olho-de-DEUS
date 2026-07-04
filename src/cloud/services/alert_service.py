"""Alert Service - Serviço de gerenciamento de alertas."""

from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class AlertLevel:
    """Níveis de alerta com thresholds."""

    LOW = "low"  # 0.50 - 0.70: Apenas log
    MEDIUM = "medium"  # 0.70 - 0.85: Revisão HITL
    HIGH = "high"  # 0.85 - 0.95: Escalar após HITL
    CRITICAL = "critical"  # >= 0.95: Notificação imediata


class AlertService:
    """
    Serviço de gerenciamento de alertas.

    Responsabilidades:
    - Classificar alertas por nível de confiança
    - Aplicar histerese para evitar flapping
    - Registrar alertas no banco de dados
    - Disparar notificações apropriadas
    """

    def __init__(
        self,
        low_threshold: float = 0.50,
        medium_threshold: float = 0.70,
        high_threshold: float = 0.85,
        critical_threshold: float = 0.95,
        hysteresis_up: float = 0.05,
        hysteresis_down: float = 0.10
    ):
        self.thresholds = {
            AlertLevel.LOW: low_threshold,
            AlertLevel.MEDIUM: medium_threshold,
            AlertLevel.HIGH: high_threshold,
            AlertLevel.CRITICAL: critical_threshold
        }
        self.hysteresis_up = hysteresis_up
        self.hysteresis_down = hysteresis_down

    def classify(
        self,
        alarm_score: float,
        previous_level: Optional[str] = None
    ) -> str:
        """
        Classifica alerta baseado no score.

        Usa histerese para evitar mudanças bruscas de nível.
        """
        # Se tem nível anterior, aplica histerese
        if previous_level:
            prev_threshold = self.thresholds.get(previous_level, 0)

            # Check downgrade com histerese down
            if alarm_score < prev_threshold - self.hysteresis_down:
                for level in [AlertLevel.LOW, AlertLevel.MEDIUM, AlertLevel.HIGH, AlertLevel.CRITICAL]:
                    if alarm_score >= self.thresholds[level] - self.hysteresis_down:
                        return level

            # Check upgrade com histerese up
            if alarm_score > prev_threshold + self.hysteresis_up:
                for level in [AlertLevel.CRITICAL, AlertLevel.HIGH, AlertLevel.MEDIUM, AlertLevel.LOW]:
                    if alarm_score >= self.thresholds[level] + self.hysteresis_up:
                        return level

        # Classificação base
        if alarm_score >= self.thresholds[AlertLevel.CRITICAL]:
            return AlertLevel.CRITICAL
        elif alarm_score >= self.thresholds[AlertLevel.HIGH]:
            return AlertLevel.HIGH
        elif alarm_score >= self.thresholds[AlertLevel.MEDIUM]:
            return AlertLevel.MEDIUM
        else:
            return AlertLevel.LOW

    def requires_hitl(self, level: str) -> bool:
        """Verifica se nível requer revisão HITL."""
        return level in [AlertLevel.MEDIUM, AlertLevel.HIGH]

    def should_notify_police(self, level: str, hitl_approved: bool = False) -> bool:
        """
        Verifica se deve notificar polícia.

        Regras:
        - CRITICAL: Notifica imediatamente (ou após HITL إذا aplicável)
        - HIGH: Notifica apenas após HITL approve
        - MEDIUM/LOW: Não notifica
        """
        if level == AlertLevel.CRITICAL:
            return True
        if level == AlertLevel.HIGH and hitl_approved:
            return True
        return False


class AlertStore:
    """
    Armazenamento de alertas em memória.

    Em produção, substituir por PostgreSQL com SQLAlchemy.
    """

    def __init__(self):
        self._alerts: dict[str, dict] = {}
        self._callbacks: List[callable] = []

    def add_alert(self, alert: dict) -> dict:
        """Adiciona alerta e notifica callbacks."""
        self._alerts[alert["id"]] = alert

        # Notifica callbacks (para WebSocket push)
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Erro em callback de alerta: {e}")

        return alert

    def get_alert(self, alert_id: str) -> Optional[dict]:
        """Obtém alerta por ID."""
        return self._alerts.get(alert_id)

    def list_alerts(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Lista alertas com filtro opcional de status."""
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.get("status") == status]

        # Ordena por timestamp decrescente
        alerts.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

        return alerts[:limit]

    def update_alert(self, alert_id: str, updates: dict) -> Optional[dict]:
        """Atualiza alerta existente."""
        if alert_id not in self._alerts:
            return None

        self._alerts[alert_id].update(updates)
        return self._alerts[alert_id]

    def register_callback(self, callback: callable):
        """Registra callback para novos alertas (WebSocket)."""
        self._callbacks.append(callback)

    @property
    def pending_count(self) -> int:
        """Conta alertas pendentes de revisão HITL."""
        return sum(
            1 for a in self._alerts.values()
            if a.get("status") == "pending"
        )


# Store global (em produção, usar banco de dados)
alert_store = AlertStore()
alert_service = AlertService()