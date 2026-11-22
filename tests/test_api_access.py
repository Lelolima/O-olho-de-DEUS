"""Controle de acesso da API HITL: toda rota de dados exige operador autenticado."""

import os

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("USE_SQLITE", "true")

from src.cloud.api.middleware import auth as auth_mod  # noqa: E402
from src.cloud.api.middleware.auth import hash_password  # noqa: E402

PROTECTED = [
    ("get", "/api/v1/alerts/"),
    ("get", "/api/v1/alerts/alert_x"),
    ("post", "/api/v1/alerts/alert_x/review"),
    ("get", "/api/v1/evidence/evt_x/chain"),
    ("post", "/api/v1/evidence/evt_x/verify"),
    ("get", "/api/v1/evidence/batch/b1"),
    ("post", "/api/v1/hitl/review"),
    ("get", "/api/v1/hitl/decisions/alert_x"),
    ("get", "/api/v1/hitl/operators/op/stats"),
    ("get", "/api/v1/hitl/dashboard/summary"),
]


@pytest.fixture(scope="module")
def client():
    from src.hitl.dashboard_server import app

    saved = auth_mod.operator_auth._users
    auth_mod.operator_auth._users = {
        "op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)}
    }
    with TestClient(app) as c:
        yield c
    auth_mod.operator_auth._users = saved


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/api/v1/auth/token", data={"username": "op", "password": "pw"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_route_requires_token(client, method, path):
    r = getattr(client, method)(path)
    assert r.status_code == 401, f"{method.upper()} {path} respondeu {r.status_code} sem token"


def test_hitl_decision_is_attributed_to_token_operator(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/alerts/",
        json={"camera_id": "CAM-9", "alarm_score": 0.9, "behavior_indicators": ["intrusao_zona"]},
        headers=headers,
    )
    assert created.status_code == 201
    alert_id = created.json()["alert_id"]

    r = client.post(
        "/api/v1/hitl/review?operator_id=outra_pessoa",
        json={"alert_id": alert_id, "decision": "dismiss", "justification": "falso positivo"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["operator_id"] == "op"
    # A decisão atualiza o alerta persistido
    got = client.get(f"/api/v1/alerts/{alert_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["status"] == "dismissed"


def test_websocket_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/alerts/ws/live") as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_websocket_accepts_valid_token(client, token):
    with client.websocket_connect(f"/api/v1/alerts/ws/live?token={token}") as ws:
        ws.send_text("ping")  # conexão aceita; servidor segue aguardando mensagens
