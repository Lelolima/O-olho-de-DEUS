"""Testes de autenticação de operadores (auditoria 2026-11-22)."""

import json
import os
import unittest

os.environ.setdefault("USE_SQLITE", "true")

from src.cloud.api.middleware.auth import (
    OperatorAuth,
    _load_users_from_env,
    hash_password,
    verify_password,
)


class TestPasswordHashing(unittest.TestCase):
    def test_hash_roundtrip(self):
        h = hash_password("s3nha-forte", iterations=1000)
        self.assertTrue(h.startswith("pbkdf2_sha256$1000$"))
        self.assertTrue(verify_password("s3nha-forte", h))
        self.assertFalse(verify_password("errada", h))

    def test_malformed_hash_is_rejected(self):
        self.assertFalse(verify_password("x", "texto-puro"))
        self.assertFalse(verify_password("x", ""))


class TestOperatorAuth(unittest.TestCase):
    def test_no_hardcoded_users_without_env(self):
        """Antes: usuários com senha em texto puro versionados no código."""
        old = os.environ.pop("OPERATOR_USERS", None)
        try:
            auth = OperatorAuth()
            self.assertEqual(auth._users, {})
            self.assertIsNone(auth.authenticate("admin", "qualquer"))
        finally:
            if old is not None:
                os.environ["OPERATOR_USERS"] = old

    def test_users_loaded_from_env(self):
        os.environ["OPERATOR_USERS"] = json.dumps(
            {
                "op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)},
                "bad": {"role": "operator", "password": "texto-puro"},
            }
        )
        try:
            users = _load_users_from_env()
        finally:
            del os.environ["OPERATOR_USERS"]
        self.assertEqual(set(users), {"op"})  # entrada sem hash é ignorada
        auth = OperatorAuth(users=users)
        self.assertEqual(auth.authenticate("op", "pw"), {"username": "op", "role": "operator"})
        self.assertIsNone(auth.authenticate("op", "errada"))
        self.assertIsNone(auth.authenticate("inexistente", "pw"))

    def test_token_roundtrip(self):
        auth = OperatorAuth(secret="x" * 32, users={})
        token = auth.create_token("op", "operator")
        info = auth.verify_token(token)
        self.assertEqual(info["username"], "op")
        self.assertIsNone(OperatorAuth(secret="y" * 32, users={}).verify_token(token))


class TestApiAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from src.cloud.api.middleware import auth as auth_mod
        from src.hitl.dashboard_server import app

        auth_mod.operator_auth._users = {
            "op": {"role": "operator", "password_hash": hash_password("pw", iterations=1000)}
        }
        cls.client = TestClient(app)

    def test_health(self):
        """Antes: a API nem importava (Integer ausente, metadata inexistente)."""
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_login_without_configured_users_is_503_with_clear_message(self):
        from src.cloud.api.middleware import auth as auth_mod

        saved = auth_mod.operator_auth._users
        auth_mod.operator_auth._users = {}
        try:
            r = self.client.post("/api/v1/auth/token", data={"username": "op", "password": "pw"})
        finally:
            auth_mod.operator_auth._users = saved
        self.assertEqual(r.status_code, 503)
        self.assertIn("OPERATOR_USERS", r.json()["detail"])

    def test_login_wrong_password(self):
        r = self.client.post("/api/v1/auth/token", data={"username": "op", "password": "x"})
        self.assertEqual(r.status_code, 401)

    def test_protected_route_requires_bearer_token(self):
        """Antes: get_current_operator usava `token = oauth2_scheme` sem Depends."""
        payload = {"camera_id": "CAM-1", "alarm_score": 0.5}
        r = self.client.post("/api/v1/alerts/", json=payload)
        self.assertEqual(r.status_code, 401)
        r = self.client.post("/api/v1/alerts/", json=payload, headers={"Authorization": "Bearer invalido"})
        self.assertEqual(r.status_code, 401)

    def test_login_then_token_accepted(self):
        r = self.client.post("/api/v1/auth/token", data={"username": "op", "password": "pw"})
        self.assertEqual(r.status_code, 200)
        token = r.json()["access_token"]
        r = self.client.post(
            "/api/v1/alerts/",
            json={"camera_id": "CAM-1", "alarm_score": 0.5},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Autenticação passou (não 401); validação/negócio decide o restante
        self.assertNotEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
