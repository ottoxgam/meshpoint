"""Route-level coverage for the update apply/rollback endpoints."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.audit import AuditLogWriter
from src.api.audit import dependencies as audit_deps
from src.api.auth import dependencies as auth_deps
from src.api.auth.jwt_session import JwtSessionService
from src.api.routes import update_routes
from src.api.update import ReleaseChannelRegistry, UpdateApplier

_SECRET = "update-routes-secret-" + "u" * 32


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(
        self, args: list[str], cwd: Optional[str], timeout_seconds: float,
    ) -> tuple[int, str, str]:
        self.calls.append(list(args))
        if args[:2] == ["git", "rev-parse"]:
            return 0, "abc123\n", ""
        return 0, "ok", ""


class TestUpdateRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = AuditLogWriter(log_path=Path(self.tmp.name) / "a.jsonl")
        self.jwt = JwtSessionService(_SECRET, expiry_minutes=60, session_version=1)
        self.runner = _FakeRunner()
        self.applier = UpdateApplier(runner=self.runner, repo_path=".")
        update_routes.init_routes(
            applier=self.applier,
            registry=ReleaseChannelRegistry(),
        )
        auth_deps.init_auth(self.jwt)
        audit_deps.init_audit(self.audit)
        app = FastAPI()
        app.include_router(update_routes.router)
        self.client = TestClient(app)
        self.admin_token = self.jwt.issue("admin", "admin")
        self.viewer_token = self.jwt.issue("viewer", "viewer")

    def tearDown(self) -> None:
        update_routes.reset_routes()
        auth_deps.reset_auth()
        audit_deps.reset_audit()
        self.tmp.cleanup()

    def test_channels_returned_for_admin(self) -> None:
        self.client.cookies.set("meshpoint_session", self.admin_token)
        response = self.client.get("/api/update/channels")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("channels", body)
        self.assertGreater(len(body["channels"]), 0)

    def test_channels_rejects_anonymous(self) -> None:
        client = TestClient(self.client.app)
        response = client.get("/api/update/channels")
        self.assertEqual(response.status_code, 401)

    def test_channels_rejects_viewer(self) -> None:
        self.client.cookies.set("meshpoint_session", self.viewer_token)
        response = self.client.get("/api/update/channels")
        self.assertEqual(response.status_code, 403)

    def test_apply_runs_chain_for_known_channel(self) -> None:
        self.client.cookies.set("meshpoint_session", self.admin_token)
        response = self.client.post(
            "/api/update/apply", json={"channel_id": "stable"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["target_branch"], "main")

    def test_apply_rejects_unknown_channel(self) -> None:
        self.client.cookies.set("meshpoint_session", self.admin_token)
        response = self.client.post(
            "/api/update/apply", json={"channel_id": "bogus"},
        )
        self.assertEqual(response.status_code, 400)

    def test_apply_rejects_custom_without_branch(self) -> None:
        self.client.cookies.set("meshpoint_session", self.admin_token)
        response = self.client.post(
            "/api/update/apply", json={"channel_id": "custom"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rollback_runs_for_admin(self) -> None:
        self.client.cookies.set("meshpoint_session", self.admin_token)
        response = self.client.post(
            "/api/update/rollback", json={"sha": "deadbeef"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])

    def test_rollback_rejects_viewer(self) -> None:
        self.client.cookies.set("meshpoint_session", self.viewer_token)
        response = self.client.post(
            "/api/update/rollback", json={"sha": "deadbeef"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
