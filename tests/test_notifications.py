"""Notificação por webhook ao escalar um alerta (servidor HTTP local real)."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_SQLITE", "true")

from src.cloud.api.middleware import auth as auth_mod
from src.cloud.api.middleware.auth import hash_password


@pytest.fixture
def webhook_server():
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/alertas", received
    server.shutdown()


@pytest.fixture
def client(monkeypatch):
    from src.hitl.dashboard_server import app

    monkeypatch.setattr(
        auth_mod.operator_auth,
        "_users",
        {"op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)}},
    )
    with TestClient(app) as c:
        token = c.post("/api/v1/auth/token", data={"username": "op", "password": "pw"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _create_alert(client, score=0.8):
    r = client.post(
        "/api/v1/alerts/",
        json={"camera_id": "CAM-1", "alarm_score": score, "behavior_indicators": ["intrusao_zona"]},
    )
    assert r.status_code == 201
    return r.json()["alert_id"]


def test_escalation_posts_to_webhook(client, webhook_server, monkeypatch):
    url, received = webhook_server
    monkeypatch.setenv("WEBHOOK_URL", url)
    alert_id = _create_alert(client)
    r = client.post("/api/v1/hitl/review", json={"alert_id": alert_id, "decision": "escalate"})
    assert r.status_code == 200
    assert received and received[-1]["alert_id"] == alert_id
    assert received[-1]["decided_by"] == "op"


def test_critical_alert_notifies_immediately(client, webhook_server, monkeypatch):
    url, received = webhook_server
    monkeypatch.setenv("WEBHOOK_URL", url)
    _create_alert(client, score=0.97)
    assert received and received[-1]["level"] == "critical"


def test_dismiss_does_not_notify(client, webhook_server, monkeypatch):
    url, received = webhook_server
    monkeypatch.setenv("WEBHOOK_URL", url)
    alert_id = _create_alert(client)
    client.post("/api/v1/hitl/review", json={"alert_id": alert_id, "decision": "dismiss"})
    assert received == []


def test_email_is_not_reported_as_sent():
    import asyncio

    from src.cloud.services.notification_service import NotificationConfig, NotificationService

    svc = NotificationService(NotificationConfig(email_recipients=["seg@example.com"]))
    result = asyncio.run(svc.send_alert({"id": "a1"}))
    assert result["email"]["success"] is False
    assert svc.get_stats()["sent"] == 0
