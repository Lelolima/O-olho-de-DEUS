"""Cadeia de custódia pela API, processador edge e serviço de fairness."""

import os
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_SQLITE", "true")

from src.cloud.api.middleware import auth as auth_mod
from src.cloud.api.middleware.auth import hash_password


@pytest.fixture
def client(tmp_path, monkeypatch):
    from src.hitl.dashboard_server import app

    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidencias"))
    monkeypatch.setattr(
        auth_mod.operator_auth,
        "_users",
        {"op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)}},
    )
    with TestClient(app) as c:
        token = c.post("/api/v1/auth/token", data={"username": "op", "password": "pw"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestEvidenceCustody:
    def test_upload_verify_and_detect_tampering(self, client, tmp_path):
        alert = client.post(
            "/api/v1/alerts/",
            json={"camera_id": "CAM-1", "alarm_score": 0.8, "behavior_indicators": ["intrusao_zona"]},
        ).json()
        content = b"\xff\xd8frame-sintetico\xff\xd9"
        up = client.post(
            f"/api/v1/evidence/upload?alert_id={alert['alert_id']}&camera_id=CAM-1",
            files={"file": ("f.jpg", content, "image/jpeg")},
        )
        assert up.status_code == 200, up.text
        body = up.json()
        stored = Path(body["frame_path"])
        assert stored.read_bytes() == content
        assert str(tmp_path / "evidencias") in str(stored)

        ok = client.post(f"/api/v1/evidence/{body['evidence_id']}/verify").json()
        assert ok["verified"] is True

        stored.write_bytes(content + b"adulterado")
        bad = client.post(f"/api/v1/evidence/{body['evidence_id']}/verify").json()
        assert bad["verified"] is False
        assert "adulterada" in bad["error"]

    def test_empty_and_oversized_uploads_rejected(self, client, monkeypatch):
        import importlib

        ev = importlib.import_module("src.cloud.api.routes.evidence")
        assert client.post("/api/v1/evidence/upload", files={"file": ("f.jpg", b"", "image/jpeg")}).status_code == 400
        monkeypatch.setattr(ev, "MAX_EVIDENCE_BYTES", 10)
        r = client.post("/api/v1/evidence/upload", files={"file": ("f.jpg", b"x" * 11, "image/jpeg")})
        assert r.status_code == 413


class TestEdgeProcessor:
    def test_missing_onnx_model_falls_back_to_haar(self):
        from src.edge.processor import EdgeAIProcessor

        proc = EdgeAIProcessor(face_model_path="modelo_inexistente.onnx", backend="onnx", device="CPU")
        info = proc.get_model_info()
        assert info["face_model_loaded"] is True
        faces, masked = proc.process_frame(np.zeros((120, 160, 3), dtype=np.uint8), extract_embedding=False)
        assert faces == []
        assert masked.shape == (120, 160, 3)

    def test_factory_from_config(self):
        from src.edge.processor import create_processor_from_config

        proc = create_processor_from_config({"backend": "haar", "device": "CPU", "thresholds": {"confidence": 0.6}})
        assert proc.confidence_threshold == 0.6


class TestFairnessService:
    def test_biased_decisions_trigger_alert_callback(self):
        from src.cloud.services.fairness_service import FairnessService

        svc = FairnessService(min_samples_for_analysis=40)
        alerts = []
        svc.register_alert_callback(lambda report, msg: alerts.append(msg))
        # Grupo B recebe muitos falsos positivos (prediction=1, ground_truth=0)
        for i in range(20):
            svc.record_decision(
                prediction=1 if i < 2 else 0, ground_truth=0, sensitive_attr="A", alert_id=f"a{i}", camera_id="C"
            )
            svc.record_decision(
                prediction=1 if i < 12 else 0, ground_truth=0, sensitive_attr="B", alert_id=f"b{i}", camera_id="C"
            )
        report = svc.run_fairness_analysis()
        assert report is not None and report["evaluable"] is True
        assert report["overall_passed"] is False
        assert alerts and "VIÉS" in alerts[0]

    def test_insufficient_samples_returns_none(self):
        from src.cloud.services.fairness_service import FairnessService

        svc = FairnessService(min_samples_for_analysis=10)
        svc.record_decision(prediction=1, ground_truth=1, sensitive_attr="A", alert_id="x", camera_id="C")
        assert svc.run_fairness_analysis() is None


def test_init_db_main_returns_zero(monkeypatch, capsys):
    from src.cloud import init_db

    assert init_db.main() == 0
    assert "[OK]" in capsys.readouterr().out


def test_reexport_modules_import():
    from src.fairness.bias_detector import BiasDetector
    from src.privacy.conditional_unblur import ConditionalUnblurer

    assert BiasDetector and ConditionalUnblurer
