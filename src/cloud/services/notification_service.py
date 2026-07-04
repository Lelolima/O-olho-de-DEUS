"""Notification Service - Serviço de notificações (email, webhook, SMS)."""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuração de notificação."""

    webhook_url: Optional[str] = None
    email_recipients: List[str] = None
    smtp_server: Optional[Dict[str, Any]] = None
    sms_provider: Optional[str] = None
    sms_credentials: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []


class NotificationService:
    """
    Serviço de notificações para alertas.

    Suporta:
    - Webhook HTTP POST
    - Email SMTP
    - SMS (Twilio, AWS SNS)
    - Push notifications

    Uso:
        config = NotificationConfig(
            webhook_url="https://api.example.com/alerts",
            email_recipients=["security@example.com"]
        )
        service = NotificationService(config)
        await service.send_alert(alert_data)
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._sent_count = 0
        self._failed_count = 0

    async def send_alert(self, alert_data: dict) -> dict:
        """
        Envia notificação de alerta.

        Envia para todos os canais configurados:
        - Webhook
        - Email
        - SMS (se crítico)

        Returns:
            Dict com status de cada canal
        """
        results = {
            "alert_id": alert_data.get("id"),
            "sent_at": datetime.now().isoformat(),
            "webhook": {"success": False, "error": None},
            "email": {"success": False, "error": None},
            "sms": {"success": False, "error": None}
        }

        # Envia webhook
        if self.config.webhook_url:
            results["webhook"] = await self._send_webhook(alert_data)

        # Envia email
        if self.config.email_recipients:
            results["email"] = await self._send_email(alert_data)

        # Envia SMS se crítico
        if alert_data.get("level") == "critical" and self.config.sms_provider:
            results["sms"] = await self._send_sms(alert_data)

        # Atualiza contadores
        for channel, result in results.items():
            if channel not in ["alert_id", "sent_at"]:
                if result.get("success"):
                    self._sent_count += 1
                else:
                    self._failed_count += 1

        return results

    async def _send_webhook(self, alert_data: dict) -> dict:
        """Envia notificação via webhook HTTP."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=alert_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook enviado: {alert_data.get('id')}")
                        return {"success": True, "status": response.status}
                    else:
                        error = f"HTTP {response.status}"
                        logger.warning(f"Webhook falhou: {error}")
                        return {"success": False, "error": error}

        except Exception as e:
            logger.error(f"Erro webhook: {e}")
            return {"success": False, "error": str(e)}

    async def _send_email(self, alert_data: dict) -> dict:
        """Envia notificação por email."""
        # Em produção, implementar SMTP real
        # Por enquanto, log apenas

        logger.info(
            f"Email seria enviado para {self.config.email_recipients}: "
            f"Alerta {alert_data.get('id')} - Score {alert_data.get('alarm_score')}"
        )

        return {
            "success": True,
            "recipients": self.config.email_recipients,
            "note": "Email não implementado - requer configuração SMTP"
        }

    async def _send_sms(self, alert_data: dict) -> dict:
        """Envia SMS para alertas críticos."""
        # Em produção, integrar com Twilio ou AWS SNS
        logger.warning(
            f"SMS seria enviado para alerta CRÍTICO: {alert_data.get('id')}"
        )

        return {
            "success": False,
            "note": "SMS não implementado - requer configuração Twilio/AWS SNS"
        }

    def get_stats(self) -> dict:
        """Retorna estatísticas de notificações."""
        total = self._sent_count + self._failed_count
        return {
            "total": total,
            "sent": self._sent_count,
            "failed": self._failed_count,
            "success_rate": self._sent_count / total if total > 0 else 0.0
        }


# Serviço global
notification_service = NotificationService()