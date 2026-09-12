from __future__ import annotations

import io
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from python.core.version import CHANNEL, VERSION


class ReleaseError(ValueError):
    """Raised for any invalid or out-of-order release operation."""


class ReleaseManager:
    """Stages, applies, discards and rolls back signed release packages
    uploaded from the MiAI Admin Android app.

    Important: applying a release does NOT hot-swap the running Python
    process's code — doing that safely from inside the same process isn't
    possible. Instead this class validates the package, tracks version
    metadata on disk, and — if present — invokes
    `scripts/apply_release.sh <zip_path>` so a real deployment (systemd,
    Docker, etc.) can perform the actual code swap and restart on its own
    terms. `/admin/release/state` reports `requires_restart` so the owner
    (and the Android app) always know whether the running process matches
    the tracked version.
    """

    def __init__(self, base_dir: str = "data/releases", hook_script: str = "scripts/apply_release.sh"):
        self.base_dir = Path(base_dir)
        self.pending_dir = self.base_dir / "pending"
        self.versions_dir = self.base_dir / "versions"
        self.state_path = self.base_dir / "state.json"
        self.hook_script = Path(hook_script)
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write_state(
                {
                    "current_version": VERSION,
                    "channel": CHANNEL,
                    "applied_at": None,
                    "pending": None,
                    "history": [],
                }
            )

    def _read_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    def state(self) -> dict[str, Any]:
        state = self._read_state()
        state["runtime_version"] = VERSION
        state["requires_restart"] = state["current_version"] != VERSION
        return state

    def upload(self, filename: str, content: bytes) -> dict[str, Any]:
        buffer = io.BytesIO(content)
        if not zipfile.is_zipfile(buffer):
            raise ReleaseError("El archivo no es un ZIP válido.")
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as zf:
            if "release.json" not in zf.namelist():
                raise ReleaseError("El paquete no contiene release.json en la raíz.")
            manifest = json.loads(zf.read("release.json").decode("utf-8"))

        version = str(manifest.get("version", "")).strip()
        channel = str(manifest.get("channel", "")).strip()
        if not version:
            raise ReleaseError("release.json del paquete no define 'version'.")

        pending_path = self.pending_dir / f"{version}.zip"
        pending_path.write_bytes(content)

        state = self._read_state()
        state["pending"] = {
            "filename": filename,
            "version": version,
            "channel": channel,
            "uploaded_at": self._now(),
            "path": str(pending_path),
        }
        self._write_state(state)
        return self.state()

    def discard(self) -> dict[str, Any]:
        state = self._read_state()
        pending = state.get("pending")
        if not pending:
            raise ReleaseError("No hay ningún paquete pendiente para descartar.")
        Path(pending["path"]).unlink(missing_ok=True)
        state["pending"] = None
        self._write_state(state)
        return self.state()

    def _run_hook(self, zip_path: str) -> None:
        if self.hook_script.exists():
            subprocess.run([str(self.hook_script), zip_path], check=False, timeout=300)

    def apply(self) -> dict[str, Any]:
        state = self._read_state()
        pending = state.get("pending")
        if not pending:
            raise ReleaseError("No hay ningún paquete pendiente para aplicar.")

        archived_dir = self.versions_dir / pending["version"]
        archived_dir.mkdir(parents=True, exist_ok=True)
        archived_path = archived_dir / "package.zip"
        shutil.move(pending["path"], archived_path)

        state["history"].append(
            {
                "version": state["current_version"],
                "channel": state.get("channel", CHANNEL),
                "applied_at": state.get("applied_at"),
            }
        )
        state["current_version"] = pending["version"]
        state["channel"] = pending["channel"] or state.get("channel", CHANNEL)
        state["applied_at"] = self._now()
        state["pending"] = None
        self._write_state(state)

        self._run_hook(str(archived_path))
        return self.state()

    def rollback(self) -> dict[str, Any]:
        state = self._read_state()
        history = state.get("history") or []
        if not history:
            raise ReleaseError("No hay versiones anteriores para revertir.")
        previous = history.pop()

        state["current_version"] = previous["version"]
        state["channel"] = previous.get("channel", state.get("channel", CHANNEL))
        state["applied_at"] = self._now()
        state["history"] = history
        self._write_state(state)

        rollback_zip = self.versions_dir / previous["version"] / "package.zip"
        if rollback_zip.exists():
            self._run_hook(str(rollback_zip))
        return self.state()
