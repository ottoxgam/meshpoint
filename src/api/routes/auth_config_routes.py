"""Auth-related configuration endpoints.

Currently a single endpoint -- ``POST /api/config/auth_lockout`` --
that updates failed-login lockout knobs from the dashboard so the
operator never has to SSH in to tune them. Distinct from
``auth_routes`` because it's about *configuration* (a dashboard-driven
change to ``local.yaml``) rather than *session lifecycle* (login,
logout, password change).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.audit import AuditLogWriter
from src.api.audit.dependencies import get_audit_writer
from src.api.auth.auth_service import AuthService
from src.api.auth.dependencies import require_admin
from src.api.auth.jwt_session import SessionClaims

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

_auth_service: AuthService | None = None


def init_routes(auth_service: AuthService) -> None:
    global _auth_service
    _auth_service = auth_service


def reset_routes() -> None:
    global _auth_service
    _auth_service = None


def _service() -> AuthService:
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth not initialized",
        )
    return _auth_service


class AuthLockoutRequest(BaseModel):
    lockout_attempts: int = Field(..., ge=1, le=100)
    lockout_cooldown_minutes: int = Field(..., ge=1, le=1440)


@router.put("/auth_lockout")
async def update_auth_lockout(
    payload: AuthLockoutRequest,
    claims: SessionClaims = Depends(require_admin),
    audit: AuditLogWriter = Depends(get_audit_writer),
) -> dict:
    """Update failed-login lockout configuration (admin only)."""
    with audit.timed_action(
        user=claims.subject,
        action="config.auth_lockout_update",
        params={
            "lockout_attempts": payload.lockout_attempts,
            "lockout_cooldown_minutes": payload.lockout_cooldown_minutes,
        },
    ):
        result = _service().update_lockout_config(
            max_attempts=payload.lockout_attempts,
            cooldown_minutes=payload.lockout_cooldown_minutes,
        )
    return {
        "lockout_attempts": result.max_attempts,
        "lockout_cooldown_minutes": result.cooldown_minutes,
    }
