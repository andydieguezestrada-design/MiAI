from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from python.admin.auth import make_owner_dependency
from python.admin.providers import ZERO_COST_PROVIDERS, build_provider
from python.admin.release_manager import ReleaseError, ReleaseManager
from python.admin.store import AdminStore
from python.admin.provider_manager import ProviderManager
from python.core.version import VERSION


class CostPolicyRequest(BaseModel):
    policy: Literal["zero_cost", "paid_allowed"]


class ProviderSwitchRequest(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)


def _file_mb(path: str) -> float:
    p = Path(path)
    return round(p.stat().st_size / (1024 * 1024), 3) if p.exists() else 0.0


def create_admin_router(engine, admin_store: AdminStore, release_manager: ReleaseManager) -> APIRouter:
    """Build the /admin router bound to a specific engine + stores.

    Built as a factory (instead of a module-level router importing `engine`
    directly from api.main) to avoid a circular import between api/main.py
    and this module.
    """
    require_owner = make_owner_dependency(admin_store)
    router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_owner)])

    def _cost_policy() -> str:
        return admin_store.get_setting("cost_policy", "zero_cost")

    def _status() -> dict:
        provider = engine.provider
        provider_name = getattr(provider, "name", "unknown")
        return {
            "cost_policy": _cost_policy(),
            "active_provider": provider_name,
            "active_model": getattr(provider, "model", "unknown"),
            "is_local": provider_name in ZERO_COST_PROVIDERS,
            "version": VERSION,
        }

    @router.get("/status")
    def status():
        return _status()

    @router.get("/stats/advanced")
    def stats_advanced():
        return {
            "tool_metrics_7d": admin_store.tool_metrics_7d(),
            "system_health": {
                "memory_db_mb": _file_mb(engine.memory.db_path),
                "audit_db_mb": admin_store.db_size_mb(),
            },
        }

    @router.post("/policy/cost")
    def set_cost_policy(body: CostPolicyRequest):
        admin_store.set_setting("cost_policy", body.policy)
        admin_store.log_audit(f"policy:cost:{body.policy}", level="admin")
        return _status()

    @router.get("/providers")
    def providers():
        """Expose routing metadata without exposing credentials."""
        return {
            "primary": _status()["active_provider"],
            "chain": [
                {
                    "name": spec.name,
                    "configured": spec.configured,
                    "model": spec.model,
                    "local": spec.local,
                }
                for spec in ProviderManager.configured_specs()
            ],
            "retries": int(os.getenv("MIAI_RETRIES", "1")),
        }

    @router.post("/provider/switch")
    def switch_provider(body: ProviderSwitchRequest):
        provider_name = body.provider.strip().lower()
        if _cost_policy() == "zero_cost" and provider_name not in ZERO_COST_PROVIDERS:
            admin_store.log_audit(
                f"provider:switch_blocked:{provider_name}",
                level="warning",
                error_message="Bloqueado por política de costo cero.",
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Política '0 costo' activa: el proveedor '{provider_name}' no está permitido. "
                    "Cambia la política a 'paid_allowed' primero si de verdad quieres usarlo."
                ),
            )
        try:
            # Keep the selected provider explicit, but automatically attach the
            # configured fallback chain. This preserves the existing switch
            # contract while making fallback a Core concern.
            fallback_names = [
                spec.name for spec in ProviderManager.configured_specs()
                if spec.name != provider_name and spec.configured
            ]
            new_provider = ProviderManager(
                provider=provider_name,
                model=body.model,
                fallback_names=fallback_names,
            ).build(strict_primary=True)
        except ValueError as exc:
            admin_store.log_audit(f"provider:switch_failed:{provider_name}", level="error", error_message=str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        engine.provider = new_provider
        engine.agent.provider = new_provider
        admin_store.log_audit(f"provider:switch:{provider_name}:{body.model}", level="admin")
        return _status()

    @router.get("/logs/{kind}")
    def logs(kind: str, limit: int = 50, offset: int = 0, level: str = ""):
        if kind not in {"audit", "system"}:
            raise HTTPException(status_code=404, detail="Tipo de log desconocido. Usa 'audit' o 'system'.")
        return admin_store.get_logs(kind, limit=limit, offset=offset, level=level)

    @router.get("/release/state")
    def release_state():
        return release_manager.state()

    @router.post("/release/upload")
    async def release_upload(file: UploadFile = File(...)):
        content = await file.read()
        try:
            state = release_manager.upload(file.filename or "release.zip", content)
        except ReleaseError as exc:
            admin_store.log_audit("release:upload_rejected", level="error", error_message=str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        admin_store.log_audit(f"release:upload:{file.filename}", level="admin")
        return state

    @router.post("/release/apply")
    def release_apply():
        try:
            state = release_manager.apply()
        except ReleaseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        admin_store.log_audit(f"release:apply:{state['current_version']}", level="admin")
        return state

    @router.post("/release/discard")
    def release_discard():
        try:
            state = release_manager.discard()
        except ReleaseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        admin_store.log_audit("release:discard", level="admin")
        return state

    @router.post("/release/rollback")
    def release_rollback():
        try:
            state = release_manager.rollback()
        except ReleaseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        admin_store.log_audit(f"release:rollback:{state['current_version']}", level="admin")
        return state

    return router
