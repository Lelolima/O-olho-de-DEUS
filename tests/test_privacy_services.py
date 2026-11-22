"""Caminhos críticos: mascaramento, criptografia, base legal, alertas, limites e configuração."""

import io
import os
from datetime import datetime, timedelta

import numpy as np
import pytest
from cryptography.fernet import Fernet, InvalidToken

os.environ.setdefault("USE_SQLITE", "true")

from src.cloud.api.middleware.rate_limiter import RateLimiter
from src.cloud.services.alert_service import AlertLevel, AlertService
from src.envfile import load_env_file, parse_env
from src.privacy.encryption import EncryptionManager
from src.privacy.legal_basis import DataCategory, LegalBasis, LegalBasisRegistry
from src.privacy.masker import BoundingBox, ConditionalUnblurer, DynamicMasker


def textured_frame(h=120, w=160):
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


class TestDynamicMasker:
    @pytest.mark.parametrize("method", ["gaussian", "pixelation", "black_box"])
    def test_masks_only_the_face_region(self, method):
        frame = textured_frame()
        box = BoundingBox(x=40, y=30, width=40, height=40)
        masked = DynamicMasker(method=method, expand_margin=0).apply(frame, [box])
        assert masked.shape == frame.shape
        assert not np.array_equal(masked[30:70, 40:80], frame[30:70, 40:80])  # rosto alterado
        np.testing.assert_array_equal(masked[:, 100:], frame[:, 100:])  # resto intacto
        if method == "black_box":
            assert masked[30:70, 40:80].max() == 0

    def test_no_faces_returns_identical_frame(self):
        frame = textured_frame()
        np.testing.assert_array_equal(DynamicMasker().apply(frame, []), frame)


class TestConditionalUnblurer:
    def test_requires_key(self):
        """Antes: sem chave o rosto era gravado em texto claro (base64)."""
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            ConditionalUnblurer(None)

    def test_roundtrip_only_with_both_keys(self):
        unblurer = ConditionalUnblurer(Fernet.generate_key())
        roi = textured_frame(32, 32)
        token = unblurer.encrypt_face_roi(roi)
        assert b"UNENCRYPTED" not in token
        with pytest.raises(PermissionError):
            unblurer.decrypt_face_roi(token, alarm_score=0.99, hitl_approved=False)
        with pytest.raises(PermissionError):
            unblurer.decrypt_face_roi(token, alarm_score=0.90, hitl_approved=True)
        restored = unblurer.decrypt_face_roi(token, alarm_score=0.99, hitl_approved=True)
        np.testing.assert_array_equal(restored, roi)  # PNG é sem perdas

    def test_plaintext_payload_is_rejected(self):
        unblurer = ConditionalUnblurer(Fernet.generate_key())
        with pytest.raises(InvalidToken):
            unblurer.decrypt_face_roi(b"UNENCRYPTED:aGVsbG8=", alarm_score=0.99, hitl_approved=True)


class TestEncryptionManager:
    def test_encrypt_decrypt_and_rotation_keeps_old_data_readable(self):
        mgr = EncryptionManager(master_key=os.urandom(32))
        old = mgr.encrypt(b"evidencia")
        old_key = old.key_id
        mgr.rotate_key()
        assert mgr.get_active_key_id() != old_key
        assert mgr.decrypt(old) == b"evidencia"
        new = mgr.encrypt(b"nova")
        assert new.key_id == mgr.get_active_key_id()
        assert mgr.decrypt(new) == b"nova"

    def test_tampered_ciphertext_fails(self):
        mgr = EncryptionManager(master_key=os.urandom(32))
        enc = mgr.encrypt(b"x")
        enc.ciphertext = enc.ciphertext[:-2] + b"AA"
        with pytest.raises(InvalidToken):
            mgr.decrypt(enc)


class TestLegalBasisRegistry:
    def test_record_id_lookup_and_expiry(self):
        reg = LegalBasisRegistry(default_controller="Condomínio X")
        rec = reg.register_processing(
            purpose="Segurança patrimonial",
            legal_basis=LegalBasis.LEGITIMO_INTERESSE,
            data_categories=[DataCategory.COMPORTAMENTO],
            retention_days=30,
        )
        assert rec.record_id.startswith("proc_")
        assert reg.get_record(rec.record_id) is rec
        assert reg.is_processing_allowed(rec.record_id)
        rec.expires_at = datetime.now() - timedelta(days=1)
        assert not reg.is_processing_allowed(rec.record_id)
        assert reg.cleanup_expired() == 1
        report = reg.generate_lgpd_report()
        assert isinstance(report, dict)


class TestAlertService:
    def test_base_levels_and_hitl_rules(self):
        svc = AlertService()
        assert svc.classify(0.2) == AlertLevel.LOW
        assert svc.classify(0.75) == AlertLevel.MEDIUM
        assert svc.classify(0.9) == AlertLevel.HIGH
        assert svc.classify(0.97) == AlertLevel.CRITICAL
        assert svc.requires_hitl(AlertLevel.HIGH) and not svc.requires_hitl(AlertLevel.CRITICAL)
        assert svc.should_notify_police(AlertLevel.CRITICAL)
        assert not svc.should_notify_police(AlertLevel.HIGH)
        assert svc.should_notify_police(AlertLevel.HIGH, hitl_approved=True)

    def test_hysteresis_avoids_flapping(self):
        svc = AlertService()
        # 0.84 está logo abaixo de HIGH (0.85), mas dentro da histerese de descida
        assert svc.classify(0.84, previous_level=AlertLevel.HIGH) == AlertLevel.HIGH
        # Sem nível anterior, 0.84 é MEDIUM
        assert svc.classify(0.84) == AlertLevel.MEDIUM
        # Queda grande (abaixo de 0.85 - 0.10) rebaixa
        assert svc.classify(0.60, previous_level=AlertLevel.HIGH) != AlertLevel.HIGH
        # Subida pequena acima de MEDIUM (dentro de +0.05) mantém MEDIUM
        assert svc.classify(0.73, previous_level=AlertLevel.MEDIUM) == AlertLevel.MEDIUM


class TestRateLimiter:
    def test_blocks_after_limit(self):
        rl = RateLimiter(requests_per_minute=3, requests_per_hour=100, burst_size=3)
        assert all(rl.is_allowed("ip")[0] for _ in range(3))
        allowed, details = rl.is_allowed("ip")
        assert not allowed and details["reason"] == "minute_limit_exceeded"
        assert rl.is_allowed("outro-ip")[0]


class TestLoginRateLimit:
    def test_login_returns_429_after_too_many_attempts(self, monkeypatch):
        import importlib

        from fastapi.testclient import TestClient

        from src.cloud.api.middleware import auth as auth_mod

        rl_mod = importlib.import_module("src.cloud.api.middleware.rate_limiter")
        from src.cloud.api.middleware.auth import hash_password
        from src.hitl.dashboard_server import app

        monkeypatch.setattr(rl_mod, "login_rate_limiter", RateLimiter(2, 100, 2))
        monkeypatch.setattr(
            auth_mod.operator_auth,
            "_users",
            {"op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)}},
        )
        client = TestClient(app)
        codes = [
            client.post("/api/v1/auth/token", data={"username": "op", "password": "x"}).status_code for _ in range(3)
        ]
        assert codes[:2] == [401, 401]
        assert codes[2] == 429


class TestEnvFile:
    def test_parse_rules(self):
        text = '# comentário\nA=1\nexport B="dois"\nC=\'{"x": 1}\'\ninvalida\n'
        assert parse_env(text) == {"A": "1", "B": "dois", "C": '{"x": 1}'}

    def test_does_not_override_real_environment(self, tmp_path, monkeypatch):
        env = tmp_path / ".env"
        env.write_text("OLHO_TESTE_A=arquivo\nOLHO_TESTE_B=arquivo\n", encoding="utf-8")
        monkeypatch.setenv("OLHO_TESTE_A", "ambiente")
        monkeypatch.delenv("OLHO_TESTE_B", raising=False)
        assert load_env_file(env) == ["OLHO_TESTE_B"]
        assert os.environ["OLHO_TESTE_A"] == "ambiente"
        assert os.environ["OLHO_TESTE_B"] == "arquivo"
        monkeypatch.delenv("OLHO_TESTE_B")


class TestBootstrapEnv:
    def test_generates_valid_env_without_printing_secrets(self, tmp_path, monkeypatch, capsys):
        import json

        from src.cloud.api.middleware.auth import verify_password
        from src.tools import bootstrap_env

        out = tmp_path / ".env"
        monkeypatch.setattr("sys.stdin", io.StringIO("uma-senha-bem-longa\n"))
        code = bootstrap_env.main(["--operator", "admin", "--role", "admin", "--output", str(out), "--password-stdin"])
        assert code == 0
        values = parse_env(out.read_text(encoding="utf-8"))
        assert len(values["JWT_SECRET"]) == 64
        Fernet(values["ENCRYPTION_KEY"].encode())  # chave Fernet válida
        users = json.loads(values["OPERATOR_USERS"])
        assert verify_password("uma-senha-bem-longa", users["admin"]["password_hash"])
        printed = capsys.readouterr().out
        assert values["JWT_SECRET"] not in printed and "uma-senha" not in printed

    def test_rejects_short_password_and_existing_file(self, tmp_path, monkeypatch):
        from src.tools import bootstrap_env

        out = tmp_path / ".env"
        monkeypatch.setattr("sys.stdin", io.StringIO("curta\n"))
        assert bootstrap_env.main(["--operator", "a", "--output", str(out), "--password-stdin"]) == 1
        out.write_text("X=1", encoding="utf-8")
        assert bootstrap_env.main(["--operator", "a", "--output", str(out), "--password-stdin"]) == 1
