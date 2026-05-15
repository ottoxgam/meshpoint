"""HTTP surface for the dashboard update + watchdog flow.

Three endpoints, all admin-only, all audited:

* ``GET  /api/update/channels`` -- enumerate available release tracks
  for the picker.
* ``POST /api/update/apply``    -- run the apply chain on the
  selected channel; returns the structured ``ApplyResult``.
* ``POST /api/update/rollback`` -- restore a prior SHA + restart
  service.

The route layer never spawns subprocesses directly: it asks the
injected :class:`UpdateApplier` to do the work. Tests provide a fake
applier so the suite never shells out.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.audit import AuditLogWriter
from src.api.audit.dependencies import get_audit_writer
from src.api.auth.dependencies import require_admin
from src.api.auth.jwt_session import SessionClaims
from src.api.update.apply import UpdateApplier
from src.api.update.channels import ReleaseChannelRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/update", tags=["update"])

_applier: UpdateApplier | None = None
_registry: ReleaseChannelRegistry | None = None


def init_routes(
    applier: UpdateApplier,
    registry: ReleaseChannelRegistry,
) -> None:
    global _applier, _registry
    _applier = applier
    _registry = registry


def reset_routes() -> None:
    global _applier, _registry
    _applier = None
    _registry = None


def _require_initialized() -> tuple[UpdateApplier, ReleaseChannelRegistry]:
    if _applier is None or _registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="update subsystem not initialized",
        )
    return _applier, _registry


class ApplyRequest(BaseModel):
    channel_id: str = Field(..., min_length=1, max_length=64)
    custom_branch: str | None = Field(default=None, max_length=200)


class RollbackRequest(BaseModel):
    sha: str = Field(..., min_length=4, max_length=80)


@router.get("/channels")
async def list_channels(
    _claims: SessionClaims = Depends(require_admin),
) -> dict:
    _applier_instance, registry = _require_initialized()
    return {"channels": registry.to_payload()}


@router.post("/apply")
async def apply_update(
    payload: ApplyRequest,
    claims: SessionClaims = Depends(require_admin),
    audit: AuditLogWriter = Depends(get_audit_writer),
) -> dict:
    applier, registry = _require_initialized()
    branch = registry.resolve_branch(
        payload.channel_id, custom_branch=payload.custom_branch,
    )
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_channel_or_branch",
        )
    with audit.timed_action(
        user=claims.subject,
        action="update.apply",
        params={"channel_id": payload.channel_id, "branch": branch},
    ) as ctx:
        result = applier.apply(branch=branch)
        ctx.params["success"] = result.success
        ctx.params["target_branch"] = result.target_branch
        if not result.success:
            ctx.params["failed_step"] = result.failed_step
            ctx.set_result("error")
    return asdict(result)


@router.post("/rollback")
async def rollback_update(
    payload: RollbackRequest,
    claims: SessionClaims = Depends(require_admin),
    audit: AuditLogWriter = Depends(get_audit_writer),
) -> dict:
    applier, _registry_instance = _require_initialized()
    with audit.timed_action(
        user=claims.subject,
        action="update.rollback",
        params={"sha": payload.sha},
    ) as ctx:
        result = applier.rollback(sha=payload.sha)
        ctx.params["success"] = result.success
        if not result.success:
            ctx.params["failed_step"] = result.failed_step
            ctx.set_result("error")
    return asdict(result)
